"""DRF views for Marketing Creatives."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets

from apps.creatives.models import Creative
from apps.creatives.serializers import CreativeSerializer
from apps.creatives.services import create_creative, delete_creative, update_creative
from common.audit import get_request_ip
from common.permissions import ReadOnlyOrManagerWrite
from common.responses import success_response


class CreativeFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by creative_type, status, and primary_campaign."""

    campaign_id = django_filters.CharFilter(field_name='campaigns__id', distinct=True)

    class Meta:
        model = Creative
        fields = ['creative_type', 'status', 'primary_campaign', 'campaign_id']


@extend_schema_view(
    list=extend_schema(tags=['Creatives'], summary='List Marketing Creatives'),
    retrieve=extend_schema(tags=['Creatives'], summary='Get Creative Asset Detail'),
    create=extend_schema(tags=['Creatives'], summary='Create Creative Asset'),
    update=extend_schema(tags=['Creatives'], summary='Replace Creative Asset'),
    partial_update=extend_schema(tags=['Creatives'], summary='Partially Update Creative Asset'),
    destroy=extend_schema(tags=['Creatives'], summary='Delete Creative Asset'),
)
class CreativeViewSet(viewsets.ModelViewSet):
    """CRUD endpoints for ad creatives and nurture assets."""

    queryset = (
        Creative.objects.select_related('primary_campaign')
        .prefetch_related('creative_campaigns')
        .order_by('id')
    )
    serializer_class = CreativeSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CreativeFilter
    search_fields = ['id', 'name', 'description']
    ordering_fields = ['id', 'name', 'creative_type', 'status', 'start_date', 'end_date', 'created_at']
    ordering = ['id']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=CreativeSerializer(instance).data,
            message='Creative retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = CreativeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creative = create_creative(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=CreativeSerializer(creative).data,
            message='Creative created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = CreativeSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_creative(
            creative=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=CreativeSerializer(updated).data,
            message='Creative updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_creative(
            creative=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Creative deleted successfully.')

