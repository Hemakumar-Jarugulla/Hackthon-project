"""DRF views and filters for Data Quality Exception listing, scanning, summary & resolution."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.exceptions.models import DataException
from apps.exceptions.serializers import (
    DataExceptionSerializer,
    ExceptionResolveRequestSerializer,
    ExceptionSummarySerializer,
)
from apps.exceptions.services.detector import detect_and_sync_exceptions
from apps.exceptions.services.workflow import (
    build_exception_summary,
    update_exception_resolution,
)
from common.audit import get_request_ip
from common.permissions import IsActiveUser, IsAnalystOrAbove
from common.responses import success_response


class DataExceptionFilter(django_filters.FilterSet):
    """FilterSet supporting filtering exceptions by severity, issue_type, status, entity, and dates."""

    created_after = django_filters.DateFilter(field_name='created_date', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_date', lookup_expr='lte')

    class Meta:
        model = DataException
        fields = [
            'severity',
            'issue_type',
            'resolution_status',
            'entity_type',
            'entity_id',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Exceptions'], summary='List Data Quality Exceptions'),
    retrieve=extend_schema(tags=['Exceptions'], summary='Get Exception Detail'),
    create=extend_schema(tags=['Exceptions'], summary='Log Data Quality Exception'),
)
class DataExceptionViewSet(viewsets.ModelViewSet):
    """Data Quality Exception management API supporting scan, summary, resolve, and reopen."""

    queryset = DataException.objects.select_related('resolved_by').all().order_by('-created_at', 'id')
    serializer_class = DataExceptionSerializer
    filterset_class = DataExceptionFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ['id', 'issue_type', 'entity_type', 'entity_id', 'description']
    ordering_fields = ['id', 'severity', 'resolution_status', 'created_date', 'created_at']
    ordering = ['-created_at', 'id']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'summary'):
            return [IsActiveUser()]
        return [IsAnalystOrAbove()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=DataExceptionSerializer(instance).data,
            message='Data exception retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = DataExceptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return success_response(
            data=DataExceptionSerializer(instance).data,
            message='Data exception logged successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=['Exceptions'],
        summary='Get Exception Summary Dashboard Metrics',
        responses={200: ExceptionSummarySerializer},
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        filtered_qs = self.filter_queryset(self.get_queryset())
        summary_data = build_exception_summary(filtered_qs)
        out = ExceptionSummarySerializer(summary_data)
        return success_response(
            data=out.data,
            message='Exception summary retrieved.',
        )

    @extend_schema(
        tags=['Exceptions'],
        summary='Scan Workspace for the 5 Core Data Quality Anomalies',
        responses={200: dict},
    )
    @action(detail=False, methods=['post'])
    def scan(self, request):
        scan_result = detect_and_sync_exceptions(
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=scan_result,
            message='Data quality anomaly scan completed.',
        )

    @extend_schema(
        tags=['Exceptions'],
        summary='Resolve or Mark Exception Reviewed',
        request=ExceptionResolveRequestSerializer,
        responses={200: DataExceptionSerializer},
    )
    @action(detail=True, methods=['patch', 'post'])
    def resolve(self, request, pk=None):
        exc = self.get_object()
        payload = {
            'resolution_status': (
                request.data.get('resolution_status')
                or request.data.get('resolutionStatus')
                or DataException.ResolutionStatus.RESOLVED
            ),
            'resolution_notes': (
                request.data.get('resolution_notes')
                if 'resolution_notes' in request.data
                else request.data.get('notes', '')
            ),
        }
        req_ser = ExceptionResolveRequestSerializer(data=payload)
        req_ser.is_valid(raise_exception=True)
        updated = update_exception_resolution(
            exception_obj=exc,
            resolution_status=req_ser.validated_data['resolution_status'],
            resolution_notes=req_ser.validated_data['resolution_notes'],
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=DataExceptionSerializer(updated).data,
            message=f'Exception updated to {updated.resolution_status}.',
        )

    @extend_schema(
        tags=['Exceptions'],
        summary='Reopen a Resolved or Reviewed Exception',
        request=ExceptionResolveRequestSerializer,
        responses={200: DataExceptionSerializer},
    )
    @action(detail=True, methods=['patch', 'post'])
    def reopen(self, request, pk=None):
        exc = self.get_object()
        notes = request.data.get('resolution_notes') or request.data.get('notes') or ''
        updated = update_exception_resolution(
            exception_obj=exc,
            resolution_status=DataException.ResolutionStatus.OPEN,
            resolution_notes=notes,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=DataExceptionSerializer(updated).data,
            message='Exception reopened cleanly.',
        )

