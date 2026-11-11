"""DRF views for Online and Offline Marketing Touchpoints."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets

from apps.touchpoints.models import Touchpoint
from apps.touchpoints.serializers import TouchpointSerializer
from apps.touchpoints.services import (
    create_touchpoint,
    delete_touchpoint_safely,
    update_touchpoint,
)
from common.audit import get_request_ip
from common.permissions import ReadOnlyOrManagerWrite
from common.responses import success_response


class TouchpointFilter(django_filters.FilterSet):
    """FilterSet supporting contact, campaign, channel, creative, session, validity, and date filters."""

    interaction_type = django_filters.CharFilter(
        field_name='interaction_type',
        lookup_expr='icontains',
    )
    missing_campaign = django_filters.BooleanFilter(
        field_name='campaign',
        lookup_expr='isnull',
    )
    timestamp_after = django_filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = django_filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')

    class Meta:
        model = Touchpoint
        fields = [
            'contact',
            'campaign',
            'channel',
            'creative',
            'session',
            'device',
            'is_online',
            'is_post_conversion',
            'is_valid',
            'interaction_type',
            'missing_campaign',
            'timestamp_after',
            'timestamp_before',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Touchpoints'], summary='List Customer Touchpoints'),
    retrieve=extend_schema(tags=['Touchpoints'], summary='Get Touchpoint Detail'),
    create=extend_schema(tags=['Touchpoints'], summary='Record Online or Offline Touchpoint'),
    update=extend_schema(tags=['Touchpoints'], summary='Replace Touchpoint'),
    partial_update=extend_schema(tags=['Touchpoints'], summary='Partially Update Touchpoint'),
    destroy=extend_schema(tags=['Touchpoints'], summary='Delete Unreferenced Touchpoint'),
)
class TouchpointViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for online and offline customer journey touchpoints."""

    queryset = (
        Touchpoint.objects.select_related('contact', 'campaign', 'channel', 'creative', 'session')
        .order_by('-timestamp', 'id')
    )
    serializer_class = TouchpointSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = TouchpointFilter
    search_fields = [
        'id',
        'interaction_type',
        'source',
        'contact__name',
        'campaign__name',
        'channel__name',
    ]
    ordering_fields = [
        'id',
        'timestamp',
        'interaction_type',
        'device',
        'is_online',
        'is_post_conversion',
        'is_valid',
        'created_at',
    ]
    ordering = ['-timestamp', 'id']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=TouchpointSerializer(instance).data,
            message='Touchpoint retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = TouchpointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        touchpoint = create_touchpoint(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=touchpoint.pk)
        return success_response(
            data=TouchpointSerializer(fresh).data,
            message='Touchpoint recorded successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = TouchpointSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_touchpoint(
            touchpoint=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        return success_response(
            data=TouchpointSerializer(fresh).data,
            message='Touchpoint updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_touchpoint_safely(
            touchpoint=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Touchpoint deleted successfully.')

