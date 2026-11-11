"""Audit trail and concurrency-safe sequence counter models."""

from django.conf import settings
from django.db import models

from common.models import TimestampedModel


class IdSequence(TimestampedModel):
    """Stores row-locked sequence counters for deterministic entity IDs."""

    scope_key = models.CharField(max_length=80, primary_key=True)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'audit_id_sequence'

    def __str__(self):
        return f'{self.scope_key}: {self.last_value}'


class AuditLog(models.Model):
    """Immutable audit log preserving historical state changes and actor attribution."""

    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        ARCHIVE = 'ARCHIVE', 'Archive'
        STATUS_CHANGE = 'STATUS_CHANGE', 'Status Change'
        ATTRIBUTION_RUN = 'ATTRIBUTION_RUN', 'Attribution Run'
        EXCEPTION_ACTION = 'EXCEPTION_ACTION', 'Exception Action'

    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    previous_state = models.JSONField(null=True, blank=True)
    new_state = models.JSONField(null=True, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id'], name='idx_audit_entity'),
            models.Index(fields=['action', 'created_at'], name='idx_audit_action_ts'),
        ]

    def __str__(self):
        return f'{self.action} {self.entity_type}({self.entity_id})'

