"""Sales Opportunity and Pipeline Stage History models."""

from decimal import Decimal

from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Opportunity(TimestampedModel):
    """Represents a B2B sales opportunity progressing through the 6 pipeline stages."""

    class Stage(models.TextChoices):
        NEW = 'New', 'New'
        QUALIFICATION = 'Qualification', 'Qualification'
        PROPOSAL = 'Proposal', 'Proposal'
        NEGOTIATION = 'Negotiation', 'Negotiation'
        CLOSED_WON = 'Closed Won', 'Closed Won'
        CLOSED_LOST = 'Closed Lost', 'Closed Lost'

    class Status(models.TextChoices):
        OPEN = 'Open', 'Open'
        WON = 'Won', 'Won'
        LOST = 'Lost', 'Lost'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    lead = models.ForeignKey(
        'leads.Lead',
        on_delete=models.PROTECT,
        related_name='opportunities',
    )
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.PROTECT,
        related_name='opportunities',
    )
    name = models.CharField(max_length=180, db_index=True)
    stage = models.CharField(
        max_length=30,
        choices=Stage.choices,
        default=Stage.NEW,
        db_index=True,
    )
    expected_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    actual_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    closing_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    class Meta:
        db_table = 'opportunities_opportunity'
        verbose_name_plural = 'Opportunities'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=Q(expected_revenue__gte=Decimal('0.00')),
                name='chk_opp_expected_rev_nonneg',
            ),
            models.CheckConstraint(
                condition=Q(actual_revenue__gte=Decimal('0.00')),
                name='chk_opp_actual_rev_nonneg',
            ),
        ]
        indexes = [
            models.Index(fields=['stage', 'status'], name='idx_opp_stage_status'),
            models.Index(fields=['closing_date', 'status'], name='idx_opp_close_status'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='OPP', model_cls=Opportunity)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.name} ({self.stage})'


class OpportunityStageHistory(models.Model):
    """Preserves stage movement history for pipeline auditability."""

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name='stage_history',
    )
    previous_stage = models.CharField(max_length=30, blank=True, default='')
    new_stage = models.CharField(max_length=30)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'opportunities_stage_history'
        ordering = ['-changed_at']

