"""CRM Lead and Lead Status History models."""

from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Lead(TimestampedModel):
    """Represents a marketing/sales qualified lead derived from a contact."""

    class Status(models.TextChoices):
        NEW = 'New', 'New'
        MQL = 'MQL', 'MQL'
        SQL = 'SQL', 'SQL'
        CONVERTED = 'Converted', 'Converted'
        DISQUALIFIED = 'Disqualified', 'Disqualified'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.PROTECT,
        related_name='leads',
    )
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='leads',
    )
    source = models.CharField(max_length=80, db_index=True)
    score = models.PositiveSmallIntegerField(default=50)
    created_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'leads_lead'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=100),
                name='chk_lead_score_range',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'created_date'], name='idx_lead_status_date'),
            models.Index(fields=['campaign', 'status'], name='idx_lead_campaign_status'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='LEAD', model_cls=Lead)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} ({self.status})'


class LeadStatusHistory(models.Model):
    """Records historical lead qualification transitions."""

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='status_history',
    )
    previous_status = models.CharField(max_length=20, blank=True, default='')
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'leads_status_history'
        ordering = ['-changed_at']

