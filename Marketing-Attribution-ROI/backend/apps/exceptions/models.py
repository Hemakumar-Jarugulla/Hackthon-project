"""Data Quality Exception tracking and resolution workflow model."""

from django.conf import settings
from django.db import models

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class DataException(TimestampedModel):
    """
    Records detected data quality and attribution anomalies without silently modifying source records.
    Covers duplicate orders, post-conversion touchpoints, currency mismatches, omitted costs,
    and unverified anonymous session links.
    """

    class IssueType(models.TextChoices):
        DUPLICATE_REVENUE = 'Revenue counted more than once', 'Revenue counted more than once'
        POST_CONVERSION_TOUCH = (
            'Touchpoint after conversion attributed',
            'Touchpoint after conversion attributed',
        )
        CURRENCY_MISMATCH = 'Spend currency mismatch', 'Spend currency mismatch'
        COSTS_OMITTED = 'Campaign costs omitted', 'Campaign costs omitted'
        UNVERIFIED_SESSION_LINK = (
            'Anonymous session linked without evidence',
            'Anonymous session linked without evidence',
        )

    class EntityType(models.TextChoices):
        ORDER = 'Order', 'Order'
        TOUCHPOINT = 'Touchpoint', 'Touchpoint'
        COST = 'Cost', 'Cost'
        CAMPAIGN = 'Campaign', 'Campaign'
        SESSION = 'Session', 'Session'

    class Severity(models.TextChoices):
        CRITICAL = 'Critical', 'Critical'
        HIGH = 'High', 'High'
        MEDIUM = 'Medium', 'Medium'
        LOW = 'Low', 'Low'

    class ResolutionStatus(models.TextChoices):
        OPEN = 'Open', 'Open'
        REVIEWED = 'Reviewed', 'Reviewed'
        RESOLVED = 'Resolved', 'Resolved'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    issue_type = models.CharField(max_length=80, choices=IssueType.choices, db_index=True)
    entity_type = models.CharField(max_length=30, choices=EntityType.choices, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, db_index=True)
    description = models.TextField()
    expected_decision = models.TextField()
    actual_decision = models.TextField()
    resolution_status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.OPEN,
        db_index=True,
    )
    created_date = models.DateField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_exceptions',
    )
    resolution_notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'exceptions_data_exception'
        ordering = ['-created_at', 'id']
        indexes = [
            models.Index(fields=['severity', 'resolution_status'], name='idx_exc_sev_status'),
            models.Index(fields=['entity_type', 'entity_id'], name='idx_exc_entity'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='EXC', model_cls=DataException)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} [{self.severity}] {self.issue_type}'

