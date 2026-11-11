"""Marketing Cost Ledger model."""

from decimal import Decimal

from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class CostRecord(TimestampedModel):
    """
    Records marketing spend line items by campaign, channel, category, currency, and date.
    Supports storing non-campaign currencies so FX mismatch exceptions can be surfaced.
    """

    class Category(models.TextChoices):
        MEDIA_SPEND = 'Media Spend', 'Media Spend'
        AGENCY = 'Agency & Bid Management', 'Agency & Bid Management'
        CREATIVE = 'Creative Production', 'Creative Production'
        PLATFORM = 'Platform & Automation', 'Platform & Automation'
        EVENT_SPONSORSHIP = 'Event Sponsorship', 'Event Sponsorship'
        OTHER = 'Other', 'Other'

    class Currency(models.TextChoices):
        USD = 'USD', 'US Dollar'
        EUR = 'EUR', 'Euro'
        GBP = 'GBP', 'British Pound'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.PROTECT,
        related_name='cost_records',
    )
    channel = models.ForeignKey(
        'channels.Channel',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='cost_records',
    )
    category = models.CharField(
        max_length=60,
        choices=Category.choices,
        default=Category.MEDIA_SPEND,
        db_index=True,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        db_index=True,
    )
    spend_date = models.DateField(db_index=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'costs_cost_record'
        ordering = ['-spend_date', 'id']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=Decimal('0.00')),
                name='chk_cost_amount_nonneg',
            ),
        ]
        indexes = [
            models.Index(fields=['campaign', 'currency'], name='idx_cost_campaign_curr'),
            models.Index(fields=['spend_date', 'category'], name='idx_cost_date_cat'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='COST', model_cls=CostRecord)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.campaign_id} ({self.amount} {self.currency})'

