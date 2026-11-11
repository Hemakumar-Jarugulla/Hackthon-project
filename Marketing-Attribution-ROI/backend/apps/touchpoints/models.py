"""Marketing Touchpoint interaction model."""

from django.db import models

from common.models import TimestampedModel
from common.sequences import generate_touchpoint_id


class Touchpoint(TimestampedModel):
    """
    Records an online or offline marketing interaction along a contact's buyer journey.
    Supports missing campaign identifiers and stores validation/post-conversion flags.
    """

    class DeviceType(models.TextChoices):
        DESKTOP = 'Desktop', 'Desktop'
        MOBILE = 'Mobile', 'Mobile'
        TABLET = 'Tablet', 'Tablet'
        OFFLINE = 'Offline', 'Offline'

    id = models.CharField(max_length=48, primary_key=True, editable=False)
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.PROTECT,
        related_name='touchpoints',
    )
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='touchpoints',
    )
    channel = models.ForeignKey(
        'channels.Channel',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='touchpoints',
    )
    creative = models.ForeignKey(
        'creatives.Creative',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='touchpoints',
    )
    session = models.ForeignKey(
        'web_sessions.WebSession',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='touchpoints',
    )
    interaction_type = models.CharField(max_length=100, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    device = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.DESKTOP,
    )
    is_online = models.BooleanField(default=True, db_index=True)
    source = models.CharField(max_length=100, blank=True, default='')
    is_post_conversion = models.BooleanField(default=False, db_index=True)
    is_valid = models.BooleanField(default=True, db_index=True)
    validation_notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'touchpoints_touchpoint'
        ordering = ['timestamp', 'id']
        indexes = [
            models.Index(fields=['contact', 'timestamp'], name='idx_tp_contact_ts'),
            models.Index(fields=['campaign', 'timestamp'], name='idx_tp_campaign_ts'),
            models.Index(fields=['is_valid', 'is_post_conversion'], name='idx_tp_validity'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_touchpoint_id(
                contact_id=self.contact_id,
                model_cls=Touchpoint,
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} ({self.interaction_type})'

