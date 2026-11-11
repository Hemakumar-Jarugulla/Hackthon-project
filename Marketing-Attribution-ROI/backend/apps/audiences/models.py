"""Marketing Audience model."""

from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Audience(TimestampedModel):
    """Represents a target marketing audience segment linked to one or more campaigns."""

    class AudienceType(models.TextChoices):
        INTENT_KEYWORDS = 'Intent Keywords', 'Intent Keywords'
        ABM = 'Account-Based (ABM)', 'Account-Based (ABM)'
        LIFECYCLE = 'Lifecycle Segment', 'Lifecycle Segment'
        RETARGETING = 'Retargeting Pool', 'Retargeting Pool'
        GEO_FIRMOGRAPHIC = 'Geo & Firmographic', 'Geo & Firmographic'
        ORGANIC = 'Organic Audience', 'Organic Audience'
        LOOKALIKE = 'Lookalike', 'Lookalike'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        DRAFT = 'Draft', 'Draft'
        ARCHIVED = 'Archived', 'Archived'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    name = models.CharField(max_length=150, unique=True)
    audience_type = models.CharField(
        max_length=50,
        choices=AudienceType.choices,
        db_index=True,
    )
    estimated_size = models.PositiveIntegerField(default=0)
    criteria = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'audiences_audience'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True)
                | Q(effective_from__isnull=True)
                | Q(effective_to__gte=models.F('effective_from')),
                name='chk_audience_effective_dates',
            ),
        ]
        indexes = [
            models.Index(fields=['audience_type', 'status'], name='idx_audience_type_status'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='AUD', model_cls=Audience)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.name}'

