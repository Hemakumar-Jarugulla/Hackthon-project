"""Closed Order & Revenue Verification model."""

from decimal import Decimal

from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Order(TimestampedModel):
    """
    Represents a customer purchase/order linked to an Opportunity and Contact.
    Stores explicit verification_status so duplicate orders can be flagged
    and excluded without silently destroying ledger history.
    """

    class Currency(models.TextChoices):
        USD = 'USD', 'US Dollar'
        EUR = 'EUR', 'Euro'
        GBP = 'GBP', 'British Pound'

    class PaymentStatus(models.TextChoices):
        PAID = 'Paid', 'Paid'
        PENDING = 'Pending', 'Pending'
        REFUNDED = 'Refunded', 'Refunded'
        FAILED = 'Failed', 'Failed'

    class VerificationStatus(models.TextChoices):
        VALID = 'Valid', 'Valid'
        DUPLICATE = 'Duplicate', 'Duplicate'
        INVALID = 'Invalid', 'Invalid'
        PENDING_REVIEW = 'Pending Review', 'Pending Review'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    # Deliberately ForeignKey (not OneToOne) so duplicate revenue anomalies can be stored & detected.
    opportunity = models.ForeignKey(
        'opportunities.Opportunity',
        on_delete=models.PROTECT,
        related_name='orders',
    )
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.PROTECT,
        related_name='orders',
    )
    order_date = models.DateField(db_index=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PAID,
        db_index=True,
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.VALID,
        db_index=True,
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'orders_order'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=Q(revenue__gte=Decimal('0.00')),
                name='chk_order_revenue_nonneg',
            ),
        ]
        indexes = [
            models.Index(
                fields=['verification_status', 'payment_status', 'order_date'],
                name='idx_order_verif_pay_date',
            ),
            models.Index(fields=['contact', 'order_date'], name='idx_order_contact_date'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='ORD', model_cls=Order)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} (${self.revenue} {self.currency} - {self.verification_status})'

