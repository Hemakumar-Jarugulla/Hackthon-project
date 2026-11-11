"""DRF views for Web Sessions and verified Contact identity linking."""

from django.db.models import Count
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.web_sessions.models import WebSession
from apps.web_sessions.serializers import (
    WebSessionLinkContactSerializer,
    WebSessionSerializer,
)
from apps.web_sessions.services import (
    create_web_session,
    delete_web_session,
    link_session_to_contact,
    update_web_session,
)
from common.audit import get_request_ip
from common.permissions import IsManagerOrAdmin, ReadOnlyOrManagerWrite
from common.responses import success_response


class WebSessionFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by contact, campaign, identity status, device, and evidence."""

    timestamp_after = django_filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_before = django_filters.IsoDateTimeFilter(field_name='timestamp', lookup_expr='lte')

    class Meta:
        model = WebSession
        fields = [
            'contact',
            'campaign',
            'identity_status',
            'device_type',
            'has_evidence',
            'anonymous_id',
            'timestamp_after',
            'timestamp_before',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Web Sessions'], summary='List Web Sessions'),
    retrieve=extend_schema(tags=['Web Sessions'], summary='Get Web Session Detail'),
    create=extend_schema(tags=['Web Sessions'], summary='Create Web Session'),
    update=extend_schema(tags=['Web Sessions'], summary='Replace Web Session'),
    partial_update=extend_schema(tags=['Web Sessions'], summary='Partially Update Web Session'),
    destroy=extend_schema(tags=['Web Sessions'], summary='Delete Web Session'),
)
class WebSessionViewSet(viewsets.ModelViewSet):
    """CRUD + verified identity-linking endpoints for Web Sessions."""

    queryset = (
        WebSession.objects.select_related('contact', 'campaign')
        .annotate(touchpoints_count=Count('touchpoints'))
        .order_by('-timestamp', 'id')
    )
    serializer_class = WebSessionSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = WebSessionFilter
    search_fields = [
        'id',
        'anonymous_id',
        'landing_page',
        'referrer',
        'contact__name',
        'campaign__name',
        'evidence_type',
    ]
    ordering_fields = [
        'id',
        'timestamp',
        'device_type',
        'identity_status',
        'has_evidence',
        'created_at',
    ]
    ordering = ['-timestamp', 'id']

    def get_serializer_class(self):
        if self.action == 'link_contact':
            return WebSessionLinkContactSerializer
        return WebSessionSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=WebSessionSerializer(instance).data,
            message='Web session retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = WebSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = create_web_session(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=session.pk)
        return success_response(
            data=WebSessionSerializer(fresh).data,
            message='Web session created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = WebSessionSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_web_session(
            session=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        return success_response(
            data=WebSessionSerializer(fresh).data,
            message='Web session updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_web_session(
            session=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Web session deleted successfully.')

    @extend_schema(
        tags=['Web Sessions'],
        summary='Link Anonymous Session to Contact with Verification Evidence',
        request=WebSessionLinkContactSerializer,
        responses={200: WebSessionSerializer},
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='link-contact',
        permission_classes=[IsManagerOrAdmin],
    )
    def link_contact(self, request, pk=None):
        instance = self.get_object()
        req_serializer = WebSessionLinkContactSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        linked = link_session_to_contact(
            session=instance,
            contact=req_serializer.validated_data['contact_id'],
            evidence_type=req_serializer.validated_data['evidence_type'],
            notes=req_serializer.validated_data.get('notes', ''),
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=linked.pk)
        return success_response(
            data=WebSessionSerializer(fresh).data,
            message='Web session linked to contact with verification evidence.',
        )

