"""DRF views for Contacts, lifecycle history, and unified customer journeys."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.contacts.models import Contact
from apps.contacts.serializers import (
    ContactJourneySerializer,
    ContactLifecycleHistorySerializer,
    ContactSerializer,
)
from apps.contacts.services import (
    create_contact,
    delete_contact_safely,
    get_contact_journey,
    get_contact_metrics_map,
    update_contact,
)
from common.audit import get_request_ip
from common.permissions import ReadOnlyOrManagerWrite
from common.responses import success_response


class ContactFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by lifecycle status, source, company, and date range."""

    company = django_filters.CharFilter(field_name='company', lookup_expr='icontains')
    source = django_filters.CharFilter(field_name='source', lookup_expr='icontains')
    created_date_after = django_filters.DateFilter(field_name='created_date', lookup_expr='gte')
    created_date_before = django_filters.DateFilter(field_name='created_date', lookup_expr='lte')

    class Meta:
        model = Contact
        fields = [
            'lifecycle_status',
            'company',
            'source',
            'created_date_after',
            'created_date_before',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Contacts'], summary='List Tracked Contacts with Engagement Rollups'),
    retrieve=extend_schema(tags=['Contacts'], summary='Get Contact Detail'),
    create=extend_schema(tags=['Contacts'], summary='Create Contact'),
    update=extend_schema(tags=['Contacts'], summary='Replace Contact'),
    partial_update=extend_schema(tags=['Contacts'], summary='Partially Update Contact'),
    destroy=extend_schema(tags=['Contacts'], summary='Delete Unreferenced Contact'),
)
class ContactViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle history + full customer journey endpoints for Contacts."""

    queryset = Contact.objects.all().order_by('id')
    serializer_class = ContactSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ContactFilter
    search_fields = ['id', 'name', 'email', 'company', 'source']
    ordering_fields = [
        'id',
        'name',
        'email',
        'company',
        'lifecycle_status',
        'created_date',
        'created_at',
    ]
    ordering = ['id']

    def get_serializer_class(self):
        if self.action == 'lifecycle':
            return ContactLifecycleHistorySerializer
        if self.action == 'journey':
            return ContactJourneySerializer
        return ContactSerializer

    def _build_serializer_context(self, instances: list[Contact]) -> dict:
        ctx = self.get_serializer_context()
        ctx['metrics_map'] = get_contact_metrics_map(instances)
        return ctx

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        items = list(page) if page is not None else list(queryset)
        serializer = ContactSerializer(
            items,
            many=True,
            context=self._build_serializer_context(items),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(data=serializer.data, message='Contacts retrieved.')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ContactSerializer(
            instance,
            context=self._build_serializer_context([instance]),
        )
        return success_response(data=serializer.data, message='Contact retrieved.')

    def create(self, request, *args, **kwargs):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = create_contact(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        out = ContactSerializer(contact, context=self._build_serializer_context([contact]))
        return success_response(
            data=out.data,
            message='Contact created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = ContactSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_contact(
            contact=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        out = ContactSerializer(updated, context=self._build_serializer_context([updated]))
        return success_response(data=out.data, message='Contact updated successfully.')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_contact_safely(
            contact=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Contact deleted successfully.')

    @extend_schema(
        tags=['Contacts'],
        summary='List Contact Lifecycle History',
        responses={200: ContactLifecycleHistorySerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='lifecycle')
    def lifecycle(self, request, pk=None):
        instance = self.get_object()
        rows = instance.lifecycle_history.all().order_by('-effective_at', '-id')
        serializer = ContactLifecycleHistorySerializer(rows, many=True)
        return success_response(
            data=serializer.data,
            message='Contact lifecycle history retrieved.',
        )

    @extend_schema(
        tags=['Contacts'],
        summary='Get Complete Customer Journey & Timeline for Contact',
        responses={200: ContactJourneySerializer},
    )
    @action(detail=True, methods=['get'], url_path='journey')
    def journey(self, request, pk=None):
        instance = self.get_object()
        model_id = request.query_params.get('model_id') or request.query_params.get('modelId')
        journey_payload = get_contact_journey(instance, model_id=model_id)
        serializer = ContactJourneySerializer(
            journey_payload,
            context=self._build_serializer_context([instance]),
        )
        return success_response(
            data=serializer.data,
            message='Customer journey retrieved.',
        )

