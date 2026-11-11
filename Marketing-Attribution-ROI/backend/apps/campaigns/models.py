"""Marketing Campaign, M2M bridge tables, and lifecycle status history models."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Campaign(TimestampedModel):
    """Represents a marketing campaign associated with a channel, creatives, and audiences."""

    class Currency(models.TextChoices):
        USD = 'USD', 'US Dollar'
        EUR = 'EUR', 'Euro'
        GBP = 'GBP', 'British Pound'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        PAUSED = 'Paused', 'Paused'
        COMPLETED = 'Completed', 'Completed'
        DRAFT = 'Draft', 'Draft'
        ARCHIVED = 'Archived', 'Archived'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    name = models.CharField(max_length=180, db_index=True)
    description = models.TextField(blank=True, default='')
    channel = models.ForeignKey(
        'channels.Channel',
        on_delete=models.PROTECT,
        related_name='campaigns',
    )
    creatives = models.ManyToManyField(
        'creatives.Creative',
        through='CampaignCreative',
        related_name='campaigns',
        blank=True,
    )
    audiences = models.ManyToManyField(
        'audiences.Audience',
        through='CampaignAudience',
        related_name='campaigns',
        blank=True,
    )
    budget = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    objective = models.CharField(max_length=120, default='Lead Generation')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    is_paid_campaign = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_campaigns',
    )

    class Meta:
        db_table = 'campaigns_campaign'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=Q(budget__gte=Decimal('0.00')),
                name='chk_campaign_budget_nonneg',
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F('start_date')),
                name='chk_campaign_valid_date_range',
            ),
        ]
        indexes = [
            models.Index(fields=['channel', 'status'], name='idx_campaign_channel_status'),
            models.Index(fields=['start_date', 'end_date'], name='idx_campaign_dates'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='CMP', model_cls=Campaign)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.name}'


class CampaignCreative(TimestampedModel):
    """Bridge table linking Campaigns and Creatives in a many-to-many relationship."""

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='campaign_creatives',
    )
    creative = models.ForeignKey(
        'creatives.Creative',
        on_delete=models.CASCADE,
        related_name='creative_campaigns',
    )
    is_primary = models.BooleanField(default=False)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'campaigns_campaign_creative'
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'creative'],
                name='uq_campaign_creative_pair',
            ),
        ]

    def __str__(self):
        return f'{self.campaign_id} <-> {self.creative_id}'


class CampaignAudience(TimestampedModel):
    """Bridge table linking Campaigns and Audiences in a many-to-many relationship."""

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='campaign_audiences',
    )
    audience = models.ForeignKey(
        'audiences.Audience',
        on_delete=models.CASCADE,
        related_name='audience_campaigns',
    )
    is_primary = models.BooleanField(default=False)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'campaigns_campaign_audience'
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'audience'],
                name='uq_campaign_audience_pair',
            ),
        ]

    def __str__(self):
        return f'{self.campaign_id} <-> {self.audience_id}'


class CampaignStatusHistory(models.Model):
    """Preserves historical lifecycle transitions for campaigns."""

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='status_history',
    )
    previous_status = models.CharField(max_length=20, blank=True, default='')
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    reason = models.TextField(blank=True, default='')
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'campaigns_status_history'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['campaign', 'changed_at'], name='idx_cmp_hist_ts'),
        ]

