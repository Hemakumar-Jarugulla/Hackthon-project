"""DRF views for Sales Opportunities and Pipeline Stage History."""

from django.db.models import Count
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.opportunities.models import Opportunity
from apps.opportunities.serializers import (
    OpportunitySerializer,
    OpportunityStageHistorySerializer,
)
from apps.opportunities.services import (
    create_opportunity,
    delete_opportunity_safely,
    update_opportunity,
)
from common.audit import get_request_ip
from common.permissions import ReadOnlyOrManagerWrite
from common.responses import success_response


class OpportunityFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by lead, contact, stage, status, closing dates, and value."""

    closing_date_after = django_filters.DateFilter(field_name='closing_date', lookup_expr='gte')
    closing_date_before = django_filters.DateFilter(field_name='closing_date', lookup_expr='lte')
    min_expected_revenue = django_filters.NumberFilter(
        field_name='expected_revenue',
        lookup_expr='gte',
    )
    max_expected_revenue = django_filters.NumberFilter(
        field_name='expected_revenue',
        lookup_expr='lte',
    )

    class Meta:
        model = Opportunity
        fields = [
            'lead',
            'contact',
            'stage',
            'status',
            'closing_date_after',
            'closing_date_before',
            'min_expected_revenue',
            'max_expected_revenue',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Opportunities'], summary='List Sales Opportunities'),
    retrieve=extend_schema(tags=['Opportunities'], summary='Get Opportunity Detail'),
    create=extend_schema(tags=['Opportunities'], summary='Create Sales Opportunity'),
    update=extend_schema(tags=['Opportunities'], summary='Replace Opportunity'),
    partial_update=extend_schema(tags=['Opportunities'], summary='Partially Update Opportunity'),
    destroy=extend_schema(tags=['Opportunities'], summary='Delete Unreferenced Opportunity'),
)
class OpportunityViewSet(viewsets.ModelViewSet):
    """CRUD + stage transition history endpoints for Sales Opportunities."""

    queryset = (
        Opportunity.objects.select_related('lead', 'contact')
        .annotate(orders_count=Count('orders'))
        .order_by('closing_date', 'id')
    )
    serializer_class = OpportunitySerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = OpportunityFilter
    search_fields = ['id', 'name', 'contact__name', 'contact__company']
    ordering_fields = [
        'id',
        'name',
        'stage',
        'status',
        'expected_revenue',
        'actual_revenue',
        'closing_date',
        'created_at',
    ]
    ordering = ['closing_date', 'id']

    def get_serializer_class(self):
        if self.action == 'history':
            return OpportunityStageHistorySerializer
        return OpportunitySerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=OpportunitySerializer(instance).data,
            message='Opportunity retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = OpportunitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opportunity = create_opportunity(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=opportunity.pk)
        return success_response(
            data=OpportunitySerializer(fresh).data,
            message='Opportunity created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = OpportunitySerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_opportunity(
            opportunity=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        return success_response(
            data=OpportunitySerializer(fresh).data,
            message='Opportunity updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_opportunity_safely(
            opportunity=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Opportunity deleted successfully.')

    @extend_schema(
        tags=['Opportunities'],
        summary='List Opportunity Stage Transition History',
        responses={200: OpportunityStageHistorySerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        instance = self.get_object()
        rows = instance.stage_history.all().order_by('-changed_at', '-id')
        serializer = OpportunityStageHistorySerializer(rows, many=True)
        return success_response(
            data=serializer.data,
            message='Opportunity stage history retrieved.',
        )

