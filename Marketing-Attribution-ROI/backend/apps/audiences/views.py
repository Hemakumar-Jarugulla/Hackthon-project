"""DRF views for Target Audiences."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.audiences.models import Audience
from apps.audiences.serializers import AudienceSerializer
from apps.audiences.services import (
    archive_audience,
    create_audience,
    delete_audience,
    update_audience,
)
from common.audit import get_request_ip
from common.permissions import IsManagerOrAdmin, ReadOnlyOrManagerWrite
from common.responses import success_response


class AudienceFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by audience_type, status, and linked campaign_id."""

    campaign_id = django_filters.CharFilter(field_name='campaigns__id', distinct=True)

    class Meta:
        model = Audience
        fields = ['audience_type', 'status', 'campaign_id']


@extend_schema_view(
    list=extend_schema(tags=['Audiences'], summary='List Marketing Audiences'),
    retrieve=extend_schema(tags=['Audiences'], summary='Get Audience Detail'),
    create=extend_schema(tags=['Audiences'], summary='Create Audience Segment'),
    update=extend_schema(tags=['Audiences'], summary='Replace Audience Segment'),
    partial_update=extend_schema(tags=['Audiences'], summary='Partially Update Audience Segment'),
    destroy=extend_schema(tags=['Audiences'], summary='Delete Audience Segment'),
)
class AudienceViewSet(viewsets.ModelViewSet):
    """CRUD + archive endpoints for target marketing audience segments."""

    queryset = Audience.objects.prefetch_related('audience_campaigns').order_by('id')
    serializer_class = AudienceSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AudienceFilter
    search_fields = ['id', 'name', 'criteria']
    ordering_fields = ['id', 'name', 'audience_type', 'estimated_size', 'status', 'created_at']
    ordering = ['id']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=AudienceSerializer(instance).data,
            message='Audience retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = AudienceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        audience = create_audience(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=AudienceSerializer(audience).data,
            message='Audience created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = AudienceSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_audience(
            audience=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=AudienceSerializer(updated).data,
            message='Audience updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_audience(
            audience=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Audience deleted successfully.')

    @extend_schema(
        tags=['Audiences'],
        summary='Archive Audience Segment',
        request=None,
        responses={200: AudienceSerializer},
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='archive',
        permission_classes=[IsManagerOrAdmin],
    )
    def archive(self, request, pk=None):
        instance = self.get_object()
        archived = archive_audience(
            audience=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(
            data=AudienceSerializer(archived).data,
            message='Audience archived successfully.',
        )

