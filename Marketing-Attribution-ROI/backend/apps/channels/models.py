"""Marketing Channel model."""

from django.db import models

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Channel(TimestampedModel):
    """Represents a marketing acquisition or engagement channel (e.g., Paid Search)."""

    class ChannelType(models.TextChoices):
        PAID_SEARCH = 'Paid Search', 'Paid Search'
        PAID_SOCIAL = 'Paid Social', 'Paid Social'
        EMAIL = 'Email', 'Email'
        DISPLAY = 'Display', 'Display'
        EVENTS = 'Events', 'Events'
        ORGANIC = 'Organic', 'Organic'
        DIRECT = 'Direct', 'Direct'
        REFERRAL = 'Referral', 'Referral'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        PAUSED = 'Paused', 'Paused'
        ARCHIVED = 'Archived', 'Archived'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    name = models.CharField(max_length=120, unique=True)
    channel_type = models.CharField(
        max_length=40,
        choices=ChannelType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    owner = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'channels_channel'
        ordering = ['id']
        indexes = [
            models.Index(fields=['channel_type', 'status'], name='idx_channel_type_status'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='CHN', model_cls=Channel)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.name}'

