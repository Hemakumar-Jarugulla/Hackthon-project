"""Read-only AuditLog REST API views for governance and traceability."""

from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from common.permissions import IsAnalystOrAbove
from common.responses import success_response


class AuditLogFilter(django_filters.FilterSet):
    """FilterSet for auditing events by entity, action, actor, and timestamp."""

    created_after = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.IsoDateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = AuditLog
        fields = ['entity_type', 'entity_id', 'action', 'actor']


@extend_schema_view(
    list=extend_schema(tags=['Audit'], summary='List Immutable Audit Log Events'),
    retrieve=extend_schema(tags=['Audit'], summary='Get Audit Log Event Detail'),
)
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit log explorer restricted to Analysts, Managers, and Admins."""

    queryset = AuditLog.objects.select_related('actor').all().order_by('-created_at', '-id')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAnalystOrAbove]
    filterset_class = AuditLogFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ['entity_type', 'entity_id', 'notes', 'actor__username']
    ordering_fields = ['created_at', 'entity_type', 'action']
    ordering = ['-created_at', '-id']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(
            data=AuditLogSerializer(instance).data,
            message='Audit log entry retrieved.',
        )

