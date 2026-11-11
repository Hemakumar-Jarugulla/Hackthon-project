"""Abstract base models shared across AttributionIQ database entities."""

from django.db import models


class TimestampedModel(models.Model):
    """Provides automatic UTC creation and update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

