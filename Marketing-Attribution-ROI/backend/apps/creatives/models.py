"""Marketing Creative asset model."""

from django.db import models
from django.db.models import Q

from common.models import TimestampedModel
from common.sequences import generate_deterministic_id


class Creative(TimestampedModel):
    """Represents an ad creative or nurture asset used across campaigns and touchpoints."""

    class CreativeType(models.TextChoices):
        RESPONSIVE_SEARCH_AD = 'Responsive Search Ad', 'Responsive Search Ad'
        CAROUSEL_AD = 'Carousel Ad', 'Carousel Ad'
        VIDEO_AD = 'Video Ad', 'Video Ad'
        EMAIL_TEMPLATE = 'Email Template', 'Email Template'
        DISPLAY_BANNER = 'Display Banner', 'Display Banner'
        EVENT_LANDING_PAGE = 'Event Landing Page', 'Event Landing Page'
        SEO_GUIDE = 'SEO Guide', 'SEO Guide'

    class Status(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        PAUSED = 'Paused', 'Paused'
        COMPLETED = 'Completed', 'Completed'
        DRAFT = 'Draft', 'Draft'

    id = models.CharField(max_length=32, primary_key=True, editable=False)
    name = models.CharField(max_length=150)
    primary_campaign = models.ForeignKey(
        'campaigns.Campaign',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='direct_creatives',
    )
    creative_type = models.CharField(
        max_length=50,
        choices=CreativeType.choices,
        db_index=True,
    )
    description = models.TextField(blank=True, default='')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    class Meta:
        db_table = 'creatives_creative'
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True)
                | Q(start_date__isnull=True)
                | Q(end_date__gte=models.F('start_date')),
                name='chk_creative_valid_dates',
            ),
        ]
        indexes = [
            models.Index(fields=['creative_type', 'status'], name='idx_creative_type_status'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_deterministic_id(prefix='CRT', model_cls=Creative)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id} - {self.name}'

