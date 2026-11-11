"""Multi-touch Attribution Model, Run, and Persisted Attribution Result models."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class AttributionModel(TimestampedModel):
    """Catalog of supported attribution models and explicit methodology configuration."""

    class ModelCode(models.TextChoices):
        FIRST_TOUCH = 'first_touch', 'First Touch'
        LAST_TOUCH = 'last_touch', 'Last Touch'
        LINEAR = 'linear', 'Linear'
        TIME_DECAY = 'time_decay', 'Time Decay'
        POSITION_BASED = 'position_based', 'Position Based'

    id = models.CharField(
        max_length=40,
        primary_key=True,
        choices=ModelCode.choices,
    )
    name = models.CharField(max_length=80)
    short_label = models.CharField(max_length=40)
    description = models.TextField()
    rule_version = models.CharField(max_length=20, default='1.0.0')
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'attribution_model'
        ordering = ['id']

    def __str__(self):
        return f'{self.name} (v{self.rule_version})'


class AttributionRun(TimestampedModel):
    """Auditable execution snapshot recording parameters, exclusions, and reconciliation totals."""

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        COMPLETED = 'Completed', 'Completed'
        FAILED = 'Failed', 'Failed'

    id = models.CharField(max_length=40, primary_key=True, editable=False)
    attribution_model = models.ForeignKey(
        AttributionModel,
        on_delete=models.PROTECT,
        related_name='runs',
    )
    rule_version = models.CharField(max_length=20, default='1.0.0')
    period_label = models.CharField(max_length=60, default='All Time')
    conversion_window_days = models.PositiveIntegerField(default=90)
    half_life_days = models.PositiveIntegerField(default=7)
    valid_orders_processed = models.PositiveIntegerField(default=0)
    excluded_duplicate_orders = models.PositiveIntegerField(default=0)
    excluded_post_conversion_touches = models.PositiveIntegerField(default=0)
    total_attributed_revenue = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
        db_index=True,
    )
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attribution_runs',
    )
    executed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'attribution_run'
        ordering = ['-executed_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(conversion_window_days__gte=1),
                name='chk_attr_run_window_pos',
            ),
            models.CheckConstraint(
                condition=Q(total_attributed_revenue__gte=Decimal('0.00')),
                name='chk_attr_run_rev_nonneg',
            ),
        ]
        indexes = [
            models.Index(
                fields=['attribution_model', 'executed_at'],
                name='idx_attr_run_model_ts',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='ATTR-RUN', model_cls=AttributionRun)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} ({self.attribution_model_id})'


class AttributionResult(TimestampedModel):
    """Persisted per-touchpoint attribution credit linked to source Order and Run."""

    id = models.CharField(max_length=40, primary_key=True, editable=False)
    run = models.ForeignKey(
        AttributionRun,
        on_delete=models.CASCADE,
        related_name='results',
    )
    attribution_model = models.ForeignKey(
        AttributionModel,
        on_delete=models.PROTECT,
        related_name='results',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='attribution_results',
    )
    touchpoint = models.ForeignKey(
        'touchpoints.Touchpoint',
        on_delete=models.PROTECT,
        related_name='attribution_results',
    )
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attribution_results',
    )
    channel = models.ForeignKey(
        'channels.Channel',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attribution_results',
    )
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.PROTECT,
        related_name='attribution_results',
    )
    rule_version = models.CharField(max_length=20, default='1.0.0')
    credit_weight = models.DecimalField(max_digits=7, decimal_places=6)
    attributed_revenue = models.DecimalField(max_digits=14, decimal_places=2)
    source_order_revenue = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    calculated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'attribution_result'
        ordering = ['order_id', 'touchpoint_id']
        constraints = [
            models.CheckConstraint(
                condition=Q(credit_weight__gte=Decimal('0.000000'))
                & Q(credit_weight__lte=Decimal('1.000000')),
                name='chk_attr_res_weight_bounds',
            ),
            models.CheckConstraint(
                condition=Q(attributed_revenue__gte=Decimal('0.00')),
                name='chk_attr_res_rev_nonneg',
            ),
            models.UniqueConstraint(
                fields=['run', 'order', 'touchpoint'],
                name='uq_attr_run_order_touch',
            ),
        ]
        indexes = [
            models.Index(fields=['run', 'campaign'], name='idx_attr_res_run_cmp'),
            models.Index(fields=['order', 'attribution_model'], name='idx_attr_res_ord_mod'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='ATTR-RES', model_cls=AttributionResult)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} -> {self.order_id} ({self.credit_weight})'

