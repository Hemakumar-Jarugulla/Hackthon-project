"""Serializer for immutable AuditLog history entries."""

from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only AuditLog representation including resolved actor username."""

    actor_username = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'entity_type',
            'entity_id',
            'action',
            'actor',
            'actor_username',
            'previous_state',
            'new_state',
            'changed_fields',
            'source_ip',
            'notes',
            'created_at',
        ]
        read_only_fields = fields

    def get_actor_username(self, obj: AuditLog) -> str | None:
        return obj.actor.username if obj.actor else None

