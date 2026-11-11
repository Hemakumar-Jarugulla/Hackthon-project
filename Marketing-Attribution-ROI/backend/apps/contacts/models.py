"""Customer Contact and Lifecycle History models."""

from django.db import models

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Contact(TimestampedModel):
    """Represents a B2B contact/buyer tracked across web sessions, touchpoints, and sales."""

    class LifecycleStatus(models.TextChoices):
        SUBSCRIBER = 'Subscriber', 'Subscriber'
        LEAD = 'Lead', 'Lead'
        OPPORTUNITY = 'Opportunity', 'Opportunity'
        CUSTOMER = 'Customer', 'Customer'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    name = models.CharField(max_length=150, db_index=True)
    email = models.EmailField(max_length=254, unique=True, db_index=True)
    phone = models.CharField(max_length=40, blank=True, default='')
    company = models.CharField(max_length=150, blank=True, default='', db_index=True)
    source = models.CharField(max_length=80, blank=True, default='Organic', db_index=True)
    created_date = models.DateField(db_index=True)
    lifecycle_status = models.CharField(
        max_length=20,
        choices=LifecycleStatus.choices,
        default=LifecycleStatus.SUBSCRIBER,
        db_index=True,
    )

    class Meta:
        db_table = 'contacts_contact'
        ordering = ['id']
        indexes = [
            models.Index(fields=['lifecycle_status', 'created_date'], name='idx_contact_lc_date'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='CON', model_cls=Contact)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.name}'


class ContactLifecycleHistory(models.Model):
    """Tracks effective lifecycle transitions for contacts (Subscriber -> Lead -> Opportunity -> Customer)."""

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='lifecycle_history',
    )
    previous_status = models.CharField(max_length=20, blank=True, default='')
    new_status = models.CharField(max_length=20)
    effective_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'contacts_lifecycle_history'
        ordering = ['-effective_at']
        indexes = [
            models.Index(fields=['contact', 'effective_at'], name='idx_con_lc_hist_ts'),
        ]

