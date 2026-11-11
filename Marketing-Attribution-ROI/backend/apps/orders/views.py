"""DRF views for Closed Orders and revenue verification status transitions."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action

from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer, OrderVerificationSerializer
from apps.orders.services import (
    create_order,
    delete_order_safely,
    update_order,
    verify_order_status,
)
from common.audit import get_request_ip
from common.permissions import IsManagerOrAdmin, ReadOnlyOrManagerWrite
from common.responses import success_response


class OrderFilter(django_filters.FilterSet):
    """FilterSet supporting filtering by opportunity, contact, statuses, currency, and dates."""

    order_date_after = django_filters.DateFilter(field_name='order_date', lookup_expr='gte')
    order_date_before = django_filters.DateFilter(field_name='order_date', lookup_expr='lte')
    min_revenue = django_filters.NumberFilter(field_name='revenue', lookup_expr='gte')
    max_revenue = django_filters.NumberFilter(field_name='revenue', lookup_expr='lte')

    class Meta:
        model = Order
        fields = [
            'opportunity',
            'contact',
            'currency',
            'payment_status',
            'verification_status',
            'order_date_after',
            'order_date_before',
            'min_revenue',
            'max_revenue',
        ]


@extend_schema_view(
    list=extend_schema(tags=['Orders'], summary='List Closed Orders'),
    retrieve=extend_schema(tags=['Orders'], summary='Get Order Detail'),
    create=extend_schema(tags=['Orders'], summary='Record Closed Order'),
    update=extend_schema(tags=['Orders'], summary='Replace Order'),
    partial_update=extend_schema(tags=['Orders'], summary='Partially Update Order'),
    destroy=extend_schema(tags=['Orders'], summary='Delete Unreferenced Order'),
)
class OrderViewSet(viewsets.ModelViewSet):
    """CRUD + verification-transition endpoints for Closed Orders."""

    queryset = Order.objects.select_related('opportunity', 'contact').order_by('-order_date', 'id')
    serializer_class = OrderSerializer
    permission_classes = [ReadOnlyOrManagerWrite]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = OrderFilter
    search_fields = ['id', 'notes', 'contact__name', 'opportunity__name']
    ordering_fields = [
        'id',
        'order_date',
        'revenue',
        'currency',
        'payment_status',
        'verification_status',
        'created_at',
    ]
    ordering = ['-order_date', 'id']

    def get_serializer_class(self):
        if self.action == 'verify':
            return OrderVerificationSerializer
        return OrderSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=OrderSerializer(instance).data,
            message='Order retrieved.',
        )

    def create(self, request, *args, **kwargs):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order(
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=order.pk)
        return success_response(
            data=OrderSerializer(fresh).data,
            message='Order created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = OrderSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = update_order(
            order=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        return success_response(
            data=OrderSerializer(fresh).data,
            message='Order updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        delete_order_safely(
            order=instance,
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        return success_response(data=None, message='Order deleted successfully.')

    @extend_schema(
        tags=['Orders'],
        summary='Update Order Verification Status (Valid / Duplicate / Invalid / Pending Review)',
        request=OrderVerificationSerializer,
        responses={200: OrderSerializer},
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='verify',
        permission_classes=[IsManagerOrAdmin],
    )
    def verify(self, request, pk=None):
        instance = self.get_object()
        req_serializer = OrderVerificationSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        updated = verify_order_status(
            order=instance,
            verification_status=req_serializer.validated_data['verification_status'],
            notes=req_serializer.validated_data.get('notes', ''),
            actor=request.user,
            source_ip=get_request_ip(request),
        )
        fresh = self.get_queryset().get(pk=updated.pk)
        return success_response(
            data=OrderSerializer(fresh).data,
            message='Order verification status updated.',
        )

