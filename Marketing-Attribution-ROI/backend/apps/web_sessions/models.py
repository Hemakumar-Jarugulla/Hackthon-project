"""Web Session and identity-resolution evidence model."""

from django.db import models

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class WebSession(TimestampedModel):
    """
    Captures anonymous or identified website sessions along with deterministic
    identity-linking evidence status to detect unverified identity links.
    """

    class IdentityStatus(models.TextChoices):
        IDENTIFIED = 'Identified', 'Identified'
        ANONYMOUS = 'Anonymous', 'Anonymous'
        UNVERIFIED_LINK = 'Unverified Link', 'Unverified Link'

    class DeviceType(models.TextChoices):
        DESKTOP = 'Desktop', 'Desktop'
        MOBILE = 'Mobile', 'Mobile'
        TABLET = 'Tablet', 'Tablet'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    anonymous_id = models.CharField(max_length=64, db_index=True)
    contact = models.ForeignKey(
        'contacts.Contact',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='web_sessions',
    )
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='web_sessions',
    )
    landing_page = models.CharField(max_length=255)
    referrer = models.CharField(max_length=255, blank=True, default='Direct')
    timestamp = models.DateTimeField(db_index=True)
    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.DESKTOP,
    )
    identity_status = models.CharField(
        max_length=24,
        choices=IdentityStatus.choices,
        default=IdentityStatus.ANONYMOUS,
        db_index=True,
    )
    has_evidence = models.BooleanField(default=False, db_index=True)
    evidence_type = models.CharField(
        max_length=80,
        blank=True,
        default='',
        help_text='e.g. Form Submission, Login Token, Email Click ID',
    )
    linking_issue = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'web_sessions_session'
        ordering = ['-timestamp', 'id']
        indexes = [
            models.Index(fields=['contact', 'timestamp'], name='idx_session_contact_ts'),
            models.Index(fields=['identity_status', 'has_evidence'], name='idx_session_identity'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='SES', model_cls=WebSession)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} ({self.identity_status})'

