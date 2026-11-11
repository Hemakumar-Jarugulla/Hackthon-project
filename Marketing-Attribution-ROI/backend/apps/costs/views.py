"""DRF views for Marketing Cost Records and FX-aware Spend Summaries."""

from django.db.models import F
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.costs.models import CostRecord
from apps.costs.serializers import CostRecordSerializer, CostSummarySerializer
from apps.costs.services import (
    build_cost_summary,
    create_cost_record,
    delete_cost_record,
    update_cost_record,
)
from common.audit import get_request_ip
from common.permissions import ReadOnlyOrManagerWrite
from common.responses import success_response


class CostRecordFilter(django_filters.FilterSet):
    """FilterSet supporting campaign, channel, category, currency, date range, and FX mismatch."""

    spend_date_after = django_filters.DateFilter(field_name='spend_date', lookup_expr='gte')
    spend_date_before = django_filters.DateFilter(field_name='spend_date', lookup_expr='lte')
    currency_mismatch = django_filters.BooleanFilter(method='filter_currency_mismatch')

    class Meta:
        model = CostRecord
        fields = [
            'campaign',
            'channel',
            'category',
            'currency',
            'spend_date_after',
            'spend_date_before',
            'currency_mismatch',
        ]

    def filter_currency_mismatch(self, queryset, name, value):
        if value is True:
            return queryset.exclude(currency=F('campaign__currency'))
        if value is False:
            return queryset.filter(currency=F('campaign__currency'))
        return queryset


@extend_schema_view(
    list=extend_schema(tags=['Costs'], summary='List Marketing Cost Records'),
    retrieve=extend_schema(tags=['Costs'], summary='Get Cost Record Detail'),
    create=extend_schema(tags=['Costs'], summary='Record Marketing Spend Line Item'),
    update=extend_schema(tags=['Costs'], summary='Replace Cost Record'),
    partial_update=extend_schema(tags=['Costs'], summary='Partially Update Cost Record'),
    destroy=extend_schema(tags=['Costs'], summary='Delete Cost Record'),
)
class CostRecordViewSet(viewsets.ModelViewSet):
    """CRUD + FX-aware ledger summary endpoints for Marketing Cost Records."""

    queryset = CostRecord.objects.select_related('campaign', 'channel').order_by('-spend_date', 'id')
    serializer_class = CostRecordSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CostRecordFilter
    search_fields = ['id', 'description', 'category', 'campaign__name', 'channel__name']
    ordering_fields = ['id', 'amount', 'currency', 'category', 'spend_date', 'created_at']
    ordering = ['-spend_date', 'id']

    def get_serializer_class(self):
        if self.action == 'summary':
            return CostSummarySerializer
        return CostRecordSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=CostRecordSerializer(instance).data,
            message='Cost record retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = CostRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = create_cost_record(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=cost.pk)
        return success_response(
            data=CostRecordSerializer(fresh).data,
            message='Cost record created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = CostRecordSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_cost_record(
            cost=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        return success_response(
            data=CostRecordSerializer(fresh).data,
            message='Cost record updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_cost_record(
            cost=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Cost record deleted successfully.')

    @extend_schema(
        tags=['Costs'],
        summary='Get Filtered Marketing Spend Summary with FX Mismatch Breakdown',
        responses={200: CostSummarySerializer},
    )
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        filtered_qs = self.filter_queryset(self.get_queryset())
        summary_data = build_cost_summary(filtered_qs)
        serializer = CostSummarySerializer(summary_data)
        return success_response(
            data=serializer.data,
            message='Marketing cost summary retrieved.',
        )

