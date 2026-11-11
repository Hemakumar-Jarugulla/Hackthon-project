"""Workspace UserProfile model extending Django's built-in User with RBAC roles."""

from django.conf import settings
from django.db import models

from common.models import TimestampedModel
from common.permissions import (
    ROLE_ADMIN,
    ROLE_MARKETING_ANALYST,
    ROLE_MARKETING_MANAGER,
    ROLE_VIEWER,
)
from common.sequences import generate_deterministic_id


class UserProfile(TimestampedModel):
    """Normalized 1:1 profile storing RBAC role, department, and workspace status."""

    class Role(models.TextChoices):
        ADMIN = ROLE_ADMIN, 'Admin'
        MARKETING_MANAGER = ROLE_MARKETING_MANAGER, 'Marketing Manager'
        MARKETING_ANALYST = ROLE_MARKETING_ANALYST, 'Marketing Analyst'
        VIEWER = ROLE_VIEWER, 'Viewer'

    class AccountStatus(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        INVITED = 'Invited', 'Invited'
        SUSPENDED = 'Suspended', 'Suspended'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    user_code = models.CharField(
        max_length=24,
        unique=True,
        blank=True,
        db_index=True,
        help_text='Deterministic display code e.g. USR-2026-0001.',
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.VIEWER,
        db_index=True,
    )
    department = models.CharField(max_length=100, default='Marketing Operations')
    timezone = models.CharField(max_length=64, default='UTC')
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    last_active_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'accounts_user_profile'
        ordering = ['user_code', 'id']
        indexes = [
            models.Index(fields=['role', 'status'], name='idx_profile_role_status'),
        ]

    def save(self, *args, **kwargs):
        if not self.user_code:
            self.user_code = generate_deterministic_id(
                prefix='USR',
                model_cls=UserProfile,
                width=4,
                id_field='user_code',
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} ({self.role})'
