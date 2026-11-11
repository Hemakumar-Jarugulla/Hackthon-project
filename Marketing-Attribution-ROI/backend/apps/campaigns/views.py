"""DRF views for Marketing Campaigns, M2M links, archiving, and status history."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.campaigns.models import Campaign
from apps.campaigns.serializers import (
    CampaignArchiveSerializer,
    CampaignReadSerializer,
    CampaignStatusHistorySerializer,
    CampaignWriteSerializer,
)
from apps.campaigns.services import (
    archive_campaign,
    create_campaign,
    delete_campaign_safely,
    get_campaign_metrics_map,
    update_campaign,
)
from common.audit import get_request_ip
from common.permissions import IsManagerOrAdmin, ReadOnlyOrManagerWrite
from common.responses import success_response


class CampaignFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by channel, status, currency, paid flag, and dates."""

    start_date_after = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    end_date_before = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')

    class Meta:
        model = Campaign
        fields = [
            'channel',
            'status',
            'currency',
            'is_paid_campaign',
            'start_date_after',
            'end_date_before',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Campaigns'], summary='List Campaigns with Spend & ROI Telemetry'),
    retrieve=extend_schema(tags=['Campaigns'], summary='Get Campaign Detail'),
    create=extend_schema(
        tags=['Campaigns'],
        summary='Create Campaign',
        request=CampaignWriteSerializer,
        responses={201: CampaignReadSerializer},
    ),
    update=extend_schema(
        tags=['Campaigns'],
        summary='Replace Campaign',
        request=CampaignWriteSerializer,
        responses={200: CampaignReadSerializer},
    ),
    partial_update=extend_schema(
        tags=['Campaigns'],
        summary='Partially Update Campaign',
        request=CampaignWriteSerializer,
        responses={200: CampaignReadSerializer},
    ),
    destroy=extend_schema(tags=['Campaigns'], summary='Delete Unreferenced Campaign'),
)
class CampaignViewSet(viewsets.ModelViewSet):
    """CRUD + archive + transition-history endpoints for Marketing Campaigns."""

    queryset = (
        Campaign.objects.select_related('channel', 'created_by')
        .prefetch_related('campaign_creatives__creative', 'campaign_audiences__audience')
        .order_by('id')
    )
    serializer_class = CampaignReadSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CampaignFilter
    search_fields = ['id', 'name', 'description', 'objective', 'channel__name']
    ordering_fields = ['id', 'name', 'budget', 'start_date', 'end_date', 'status', 'created_at']
    ordering = ['id']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CampaignWriteSerializer
        if self.action == 'archive':
            return CampaignArchiveSerializer
        if self.action == 'history':
            return CampaignStatusHistorySerializer
        return CampaignReadSerializer

    def _build_read_context(self, instances: list[Campaign]) -> dict:
        ctx = self.get_serializer_context()
        model_id = self.request.query_params.get('model_id')
        ctx['metrics_map'] = get_campaign_metrics_map(instances, model_id=model_id)
        return ctx

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        items = list(page) if page is not None else list(queryset)
        serializer = CampaignReadSerializer(
            items,
            many=True,
            context=self._build_read_context(items),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(data=serializer.data, message='Campaigns retrieved.')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CampaignReadSerializer(
            instance,
            context=self._build_read_context([instance]),
        )
        return success_response(data=serializer.data, message='Campaign retrieved.')

    def create(self, request, *args, **kwargs):
        serializer = CampaignWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = create_campaign(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        # Re-fetch with prefetched relations for clean read output
        fresh = self.get_queryset().get(pk=campaign.pk)
        out = CampaignReadSerializer(fresh, context=self._build_read_context([fresh]))
        return success_response(
            data=out.data,
            message='Campaign created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = CampaignWriteSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_campaign(
            campaign=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        out = CampaignReadSerializer(fresh, context=self._build_read_context([fresh]))
        return success_response(data=out.data, message='Campaign updated successfully.')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_campaign_safely(
            campaign=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Campaign deleted successfully.')

    @extend_schema(
        tags=['Campaigns'],
        summary='Archive Campaign',
        request=CampaignArchiveSerializer,
        responses={200: CampaignReadSerializer},
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='archive',
        permission_classes=[IsManagerOrAdmin],
    )
    def archive(self, request, pk=None):
        instance = self.get_object()
        req_serializer = CampaignArchiveSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        archived = archive_campaign(
            campaign=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
            reason=req_serializer.validated_data.get('reason', ''),
        )
        fresh = self.get_queryset().get(pk=archived.pk)
        out = CampaignReadSerializer(fresh, context=self._build_read_context([fresh]))
        return success_response(data=out.data, message='Campaign archived successfully.')

    @extend_schema(
        tags=['Campaigns'],
        summary='List Campaign Status Transition History',
        responses={200: CampaignStatusHistorySerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        instance = self.get_object()
        rows = instance.status_history.select_related('changed_by').order_by('-changed_at')
        serializer = CampaignStatusHistorySerializer(rows, many=True)
        return success_response(
            data=serializer.data,
            message='Campaign status history retrieved.',
        )

