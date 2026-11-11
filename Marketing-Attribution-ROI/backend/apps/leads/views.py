"""DRF views for Marketing & Sales Qualified Leads."""

from django.db.models import Count
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.leads.models import Lead
from apps.leads.serializers import LeadSerializer, LeadStatusHistorySerializer
from apps.leads.services import create_lead, delete_lead_safely, update_lead
from common.audit import get_request_ip
from common.permissions import ReadOnlyOrManagerWrite
from common.responses import success_response


class LeadFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by contact, campaign, status, score, and date range."""

    source = django_filters.CharFilter(field_name='source', lookup_expr='icontains')
    score_min = django_filters.NumberFilter(field_name='score', lookup_expr='gte')
    score_max = django_filters.NumberFilter(field_name='score', lookup_expr='lte')
    created_date_after = django_filters.DateFilter(field_name='created_date', lookup_expr='gte')
    created_date_before = django_filters.DateFilter(field_name='created_date', lookup_expr='lte')
    missing_campaign = django_filters.BooleanFilter(field_name='campaign', lookup_expr='isnull')

    class Meta:
        model = Lead
        fields = [
            'contact',
            'campaign',
            'status',
            'source',
            'score_min',
            'score_max',
            'created_date_after',
            'created_date_before',
            'missing_campaign',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Leads'], summary='List Leads'),
    retrieve=extend_schema(tags=['Leads'], summary='Get Lead Detail'),
    create=extend_schema(tags=['Leads'], summary='Create Lead'),
    update=extend_schema(tags=['Leads'], summary='Replace Lead'),
    partial_update=extend_schema(tags=['Leads'], summary='Partially Update Lead'),
    destroy=extend_schema(tags=['Leads'], summary='Delete Unreferenced Lead'),
)
class LeadViewSet(viewsets.ModelViewSet):
    """CRUD + qualification transition history endpoints for Leads."""

    queryset = (
        Lead.objects.select_related('contact', 'campaign')
        .annotate(opportunities_count=Count('opportunities'))
        .order_by('-created_date', 'id')
    )
    serializer_class = LeadSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = LeadFilter
    search_fields = ['id', 'source', 'contact__name', 'contact__company', 'campaign__name']
    ordering_fields = ['id', 'score', 'status', 'created_date', 'converted_at', 'created_at']
    ordering = ['-created_date', 'id']

    def get_serializer_class(self):
        if self.action == 'history':
            return LeadStatusHistorySerializer
        return LeadSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=LeadSerializer(instance).data,
            message='Lead retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = LeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = create_lead(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=lead.pk)
        return success_response(
            data=LeadSerializer(fresh).data,
            message='Lead created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = LeadSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_lead(
            lead=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        return success_response(
            data=LeadSerializer(fresh).data,
            message='Lead updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_lead_safely(
            lead=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Lead deleted successfully.')

    @extend_schema(
        tags=['Leads'],
        summary='List Lead Status Transition History',
        responses={200: LeadStatusHistorySerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        instance = self.get_object()
        rows = instance.status_history.all().order_by('-changed_at', '-id')
        serializer = LeadStatusHistorySerializer(rows, many=True)
        return success_response(
            data=serializer.data,
            message='Lead status history retrieved.',
        )

