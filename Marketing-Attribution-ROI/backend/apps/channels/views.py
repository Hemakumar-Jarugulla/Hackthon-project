"""DRF views for Marketing Channels."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.channels.models import Channel
from apps.channels.serializers import ChannelSerializer
from apps.channels.services import (
    archive_channel,
    create_channel,
    delete_channel_safely,
    get_channel_metrics_map,
    update_channel,
)
from common.audit import get_request_ip
from common.permissions import IsManagerOrAdmin, ReadOnlyOrManagerWrite
from common.responses import success_response


class ChannelFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by channel_type, status, and owner."""

    owner = django_filters.CharFilter(field_name='owner', lookup_expr='icontains')

    class Meta:
        model = Channel
        fields = ['channel_type', 'status', 'owner']


@extend_schema_view(
    list=extend_schema(tags=['Channels'], summary='List Marketing Channels with ROI Metrics'),
    retrieve=extend_schema(tags=['Channels'], summary='Get Marketing Channel Detail'),
    create=extend_schema(tags=['Channels'], summary='Create Marketing Channel'),
    update=extend_schema(tags=['Channels'], summary='Replace Marketing Channel'),
    partial_update=extend_schema(tags=['Channels'], summary='Partially Update Marketing Channel'),
    destroy=extend_schema(tags=['Channels'], summary='Delete Unreferenced Marketing Channel'),
)
class ChannelViewSet(viewsets.ModelViewSet):
    """CRUD + archive endpoints for marketing channels with live attribution metrics."""

    queryset = Channel.objects.all().order_by('id')
    serializer_class = ChannelSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ChannelFilter
    search_fields = ['id', 'name', 'owner', 'description']
    ordering_fields = ['id', 'name', 'channel_type', 'status', 'created_at']
    ordering = ['id']

    def _build_serializer_context(self, instances: list[Channel]) -> dict:
        ctx = self.get_serializer_context()
        model_id = self.request.query_params.get('model_id')
        ctx['metrics_map'] = get_channel_metrics_map(instances, model_id=model_id)
        return ctx

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        items = list(page) if page is not None else list(queryset)
        serializer = ChannelSerializer(
            items,
            many=True,
            context=self._build_serializer_context(items),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(data=serializer.data, message='Channels retrieved.')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ChannelSerializer(
            instance,
            context=self._build_serializer_context([instance]),
        )
        return success_response(data=serializer.data, message='Channel retrieved.')

    def create(self, request, *args, **kwargs):
        serializer = ChannelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel = create_channel(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        out = ChannelSerializer(channel, context=self._build_serializer_context([channel]))
        return success_response(
            data=out.data,
            message='Channel created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = ChannelSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_channel(
            channel=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        out = ChannelSerializer(updated, context=self._build_serializer_context([updated]))
        return success_response(data=out.data, message='Channel updated successfully.')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_channel_safely(
            channel=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Channel deleted successfully.')

    @extend_schema(
        tags=['Channels'],
        summary='Archive Marketing Channel',
        request=None,
        responses={200: ChannelSerializer},
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='archive',
        permission_classes=[IsManagerOrAdmin],
    )
    def archive(self, request, pk=None):
        instance = self.get_object()
        archived = archive_channel(
            channel=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        out = ChannelSerializer(archived, context=self._build_serializer_context([archived]))
        return success_response(data=out.data, message='Channel archived successfully.')

