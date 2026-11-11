"""DRF views for Attribution Models, Engine Execution, Model Comparison, Runs, and Results."""

from django.db.models import Count
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun
from apps.attribution.serializers import (
    AttributionComparisonResponseSerializer,
    AttributionExecuteRequestSerializer,
    AttributionExecuteResponseSerializer,
    AttributionModelSerializer,
    AttributionResultSerializer,
    AttributionRunDetailSerializer,
    AttributionRunSerializer,
)
from apps.attribution.services.attribution_engine import (
    compare_attribution_models,
    ensure_attribution_models_seeded,
    execute_attribution_run,
    serialize_run_payload,
    update_attribution_model,
)
from common.audit import get_request_ip
from common.permissions import IsAnalystOrAbove, ReadOnlyOrManagerWrite, is_active_account
from common.responses import success_response


def _extract_run_query_params(request) -> dict:
    """Normalize snake_case and camelCase query parameters cleanly for attribution APIs."""
    qp = request.query_params
    payload = {}
    if 'model_id' in qp or 'modelId' in qp:
        payload['model_id'] = qp.get('model_id') or qp.get('modelId')
    if 'conversion_window_days' in qp or 'conversionWindowDays' in qp:
        payload['conversion_window_days'] = qp.get('conversion_window_days') or qp.get(
            'conversionWindowDays'
        )
    if 'half_life_days' in qp or 'halfLifeDays' in qp:
        payload['half_life_days'] = qp.get('half_life_days') or qp.get('halfLifeDays')
    if 'date_range' in qp or 'dateRange' in qp:
        payload['date_range'] = qp.get('date_range') or qp.get('dateRange')
    if 'date_from' in qp:
        payload['date_from'] = qp.get('date_from')
    if 'date_to' in qp:
        payload['date_to'] = qp.get('date_to')
    if 'period_label' in qp:
        payload['period_label'] = qp.get('period_label')
    return payload


class ActiveUserReadPermission(IsAuthenticated):
    """Require authenticated and non-suspended user for read-only analytics endpoints."""

    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and is_active_account(request.user))


@extend_schema_view(
    list=extend_schema(tags=['Attribution'], summary='List Attribution Models'),
    retrieve=extend_schema(tags=['Attribution'], summary='Get Attribution Model Configuration'),
    update=extend_schema(tags=['Attribution'], summary='Update Attribution Model Configuration'),
    partial_update=extend_schema(
        tags=['Attribution'],
        summary='Partially Update Attribution Model Configuration',
    ),
)
class AttributionModelViewSet(viewsets.ModelViewSet):
    """Read + Manager/Admin configuration endpoints for the 5 attribution models."""

    queryset = AttributionModel.objects.all().order_by('id')
    serializer_class = AttributionModelSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    http_method_names = ['get', 'put', 'patch', 'head', 'options']
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active']
    ordering_fields = ['id', 'name', 'rule_version']
    ordering = ['id']

    def get_queryset(self):
        ensure_attribution_models_seeded()
        return AttributionModel.objects.all().order_by('id')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=AttributionModelSerializer(instance).data,
            message='Attribution model retrieved.',
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = AttributionModelSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_attribution_model(
            model_obj=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=AttributionModelSerializer(updated).data,
            message='Attribution model updated successfully.',
        )


class AttributionRunFilter(django_filters.FilterSet):
    """FilterSet supporting filtering attribution execution runs by model, status, and timestamps."""

    executed_after = django_filters.IsoDateTimeFilter(field_name='executed_at', lookup_expr='gte')
    executed_before = django_filters.IsoDateTimeFilter(field_name='executed_at', lookup_expr='lte')

    class Meta:
        model = AttributionRun
        fields = ['attribution_model', 'status', 'executed_after', 'executed_before']


@extend_schema_view(
    list=extend_schema(tags=['Attribution'], summary='List Persisted Attribution Runs'),
    retrieve=extend_schema(
        tags=['Attribution'],
        summary='Get Attribution Run Breakdown & Results',
        responses={200: AttributionRunDetailSerializer},
    ),
)
class AttributionRunViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit history of persisted AttributionRun executions."""

    queryset = (
        AttributionRun.objects.select_related('attribution_model', 'executed_by')
        .annotate(result_rows_count=Count('results'))
        .order_by('-executed_at', 'id')
    )
    serializer_class = AttributionRunSerializer
    permission_classes = [ActiveUserReadPermission]
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = AttributionRunFilter
    ordering_fields = ['id', 'executed_at', 'total_attributed_revenue', 'valid_orders_processed']
    ordering = ['-executed_at', 'id']

    def retrieve(self, request, *args, **kwargs):
        run = self.get_object()
        detail_payload = serialize_run_payload(run)
        serializer = AttributionRunDetailSerializer(detail_payload)
        return success_response(
            data=serializer.data,
            message='Attribution run details retrieved.',
        )


class AttributionResultFilter(django_filters.FilterSet):
    """FilterSet supporting auditing AttributionResult rows by run, order, campaign, and contact."""

    class Meta:
        model = AttributionResult
        fields = [
            'run',
            'attribution_model',
            'order',
            'touchpoint',
            'campaign',
            'channel',
            'contact',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Attribution'], summary='List Per-Touchpoint Attribution Results'),
    retrieve=extend_schema(tags=['Attribution'], summary='Get Attribution Result Row'),
)
class AttributionResultViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ledger of traceable per-touchpoint credit allocations."""

    queryset = AttributionResult.objects.select_related(
        'attribution_model',
        'order',
        'touchpoint',
        'campaign',
        'channel',
        'contact',
    ).order_by('-calculated_at', 'order_id', 'touchpoint_id')
    serializer_class = AttributionResultSerializer
    permission_classes = [ActiveUserReadPermission]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AttributionResultFilter
    search_fields = [
        'id',
        'order__id',
        'touchpoint__id',
        'campaign__name',
        'channel__name',
        'contact__name',
    ]
    ordering_fields = [
        'id',
        'credit_weight',
        'attributed_revenue',
        'calculated_at',
        'order__order_date',
    ]
    ordering = ['-calculated_at', 'order_id', 'touchpoint_id']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=AttributionResultSerializer(instance).data,
            message='Attribution result retrieved.',
        )


class AttributionExecuteView(APIView):
    """
    Execute an attribution model calculation (`POST`, Analysts/Managers/Admins, persists run)
    or preview attribution metrics without mutating DB (`GET`, authenticated read roles).
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAnalystOrAbove()]
        return [ActiveUserReadPermission()]

    @extend_schema(
        tags=['Attribution'],
        summary='Preview Attribution Calculation (Non-Persisting)',
        parameters=[
            OpenApiParameter('model_id', str, required=False, description='Attribution model code'),
            OpenApiParameter('conversion_window_days', int, required=False),
            OpenApiParameter('half_life_days', int, required=False),
            OpenApiParameter('date_range', str, required=False),
        ],
        responses={200: AttributionExecuteResponseSerializer},
    )
    def get(self, request):
        params = _extract_run_query_params(request)
        params['persist'] = False
        req_ser = AttributionExecuteRequestSerializer(data=params)
        req_ser.is_valid(raise_exception=True)
        result = execute_attribution_run(**req_ser.validated_data)
        out = AttributionExecuteResponseSerializer(result)
        return success_response(data=out.data, message='Attribution preview calculated.')

    @extend_schema(
        tags=['Attribution'],
        summary='Run Attribution Engine and Persist Results',
        request=AttributionExecuteRequestSerializer,
        responses={
            201: AttributionExecuteResponseSerializer,
            200: AttributionExecuteResponseSerializer,
        },
    )
    def post(self, request):
        req_ser = AttributionExecuteRequestSerializer(data=request.data)
        req_ser.is_valid(raise_exception=True)
        result = execute_attribution_run(
            **req_ser.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        out = AttributionExecuteResponseSerializer(result)
        http_status = (
            status.HTTP_201_CREATED if result['persisted'] else status.HTTP_200_OK
        )
        return success_response(
            data=out.data,
            message='Attribution engine executed successfully.',
            status_code=http_status,
        )


class AttributionCompareView(APIView):
    """Compare all 5 attribution models side-by-side in Recharts-ready JSON format."""

    permission_classes = [ActiveUserReadPermission]

    @extend_schema(
        tags=['Attribution'],
        summary='Compare All 5 Attribution Models Side-by-Side',
        parameters=[
            OpenApiParameter('conversion_window_days', int, required=False),
            OpenApiParameter('half_life_days', int, required=False),
            OpenApiParameter('date_range', str, required=False),
            OpenApiParameter('date_from', str, required=False),
            OpenApiParameter('date_to', str, required=False),
        ],
        responses={200: AttributionComparisonResponseSerializer},
    )
    def get(self, request):
        params = _extract_run_query_params(request)
        req_ser = AttributionExecuteRequestSerializer(data=params)
        req_ser.is_valid(raise_exception=True)
        comparison = compare_attribution_models(
            conversion_window_days=req_ser.validated_data.get('conversion_window_days'),
            half_life_days=req_ser.validated_data.get('half_life_days'),
            date_range=req_ser.validated_data.get('date_range'),
            date_from=req_ser.validated_data.get('date_from'),
            date_to=req_ser.validated_data.get('date_to'),
        )
        out = AttributionComparisonResponseSerializer(comparison)
        return success_response(
            data=out.data,
            message='Attribution model comparison retrieved.',
        )

