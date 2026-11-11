"""Persisted Data Validation suite run and check result models."""

from django.db import models

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class ValidationRun(TimestampedModel):
    """Stores summary telemetry for an execution of the data validation suite."""

    id = models.CharField(max_length=40, primary_key=True, editable=False)
    executed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    triggered_by = models.CharField(max_length=100, default='System Schedule')
    total_checks = models.PositiveIntegerField(default=0)
    passed_checks = models.PositiveIntegerField(default=0)
    failed_checks = models.PositiveIntegerField(default=0)
    warning_checks = models.PositiveIntegerField(default=0)
    total_records_checked = models.PositiveIntegerField(default=0)
    total_invalid_records = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'validation_run'
        ordering = ['-executed_at']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='VAL-RUN', model_cls=ValidationRun)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} (Passed={self.passed_checks}, Failed={self.failed_checks})'


class ValidationCheckResult(TimestampedModel):
    """Stores individual rule outcomes linked to a ValidationRun."""

    class Status(models.TextChoices):
        PASSED = 'Passed', 'Passed'
        FAILED = 'Failed', 'Failed'
        WARNING = 'Warning', 'Warning'

    run = models.ForeignKey(
        ValidationRun,
        on_delete=models.CASCADE,
        related_name='checks',
    )
    check_code = models.CharField(max_length=20, db_index=True)
    check_name = models.CharField(max_length=120)
    category = models.CharField(max_length=80, db_index=True)
    entity = models.CharField(max_length=100)
    records_checked = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    details = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'validation_check_result'
        ordering = ['check_code']
        constraints = [
            models.UniqueConstraint(
                fields=['run', 'check_code'],
                name='uq_val_run_check_code',
            ),
        ]

    def __str__(self):
        return f'{self.check_code} [{self.status}]'

