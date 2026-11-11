"""Business services for user provisioning, JWT issuance, RBAC enforcement, and auditing."""

import logging
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserProfile
from apps.audit.models import AuditLog
from common.permissions import ROLE_ADMIN

User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request) -> str | None:
    """Extract client IP address from request headers safely."""
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def split_full_name(full_name: str) -> tuple[str, str]:
    """Split a display name into (first_name, last_name)."""
    cleaned = (full_name or '').strip()
    if not cleaned:
        return '', ''
    parts = cleaned.split(None, 1)
    first_name = parts[0][:150]
    last_name = parts[1][:150] if len(parts) > 1 else ''
    return first_name, last_name


def derive_unique_username(email: str, preferred_username: str = '') -> str:
    """Derive a unique username from preferred input or email local-part."""
    raw_base = (preferred_username or '').strip() or (email.split('@', 1)[0] if '@' in email else email)
    sanitized = re.sub(r'[^a-zA-Z0-9._+-]', '_', raw_base).strip('_') or 'user'
    candidate = sanitized[:140]
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        tail = f'_{suffix}'
        candidate = f'{sanitized[: 150 - len(tail)]}{tail}'
        suffix += 1
    return candidate


def serialize_user_snapshot(user) -> dict:
    """Return a non-sensitive state snapshot dictionary for AuditLog persistence."""
    profile = getattr(user, 'profile', None)
    return {
        'id': user.pk,
        'user_code': profile.user_code if profile else '',
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'role': ROLE_ADMIN if user.is_superuser else (profile.role if profile else UserProfile.Role.VIEWER),
        'department': profile.department if profile else '',
        'timezone': profile.timezone if profile else 'UTC',
        'status': profile.status if profile else UserProfile.AccountStatus.ACTIVE,
    }


def log_account_audit(
    *,
    target_user,
    action: str,
    actor=None,
    previous_state=None,
    new_state=None,
    changed_fields=None,
    source_ip=None,
    notes='',
):
    """Persist an immutable AuditLog row for account lifecycle operations."""
    profile = getattr(target_user, 'profile', None)
    entity_id = profile.user_code if profile and profile.user_code else str(target_user.pk)
    AuditLog.objects.create(
        entity_type='User',
        entity_id=entity_id,
        action=action,
        actor=actor if (actor and getattr(actor, 'is_authenticated', False)) else None,
        previous_state=previous_state,
        new_state=new_state,
        changed_fields=changed_fields or [],
        source_ip=source_ip,
        notes=notes,
    )


def get_or_create_user_profile(
    user,
    *,
    default_role: str | None = None,
    department: str = 'Marketing Operations',
    timezone_name: str = 'UTC',
    status: str = UserProfile.AccountStatus.ACTIVE,
) -> UserProfile:
    """Fetch existing UserProfile or provision one automatically for superusers/legacy accounts."""
    resolved_role = default_role or (
        UserProfile.Role.ADMIN if user.is_superuser else UserProfile.Role.VIEWER
    )
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': resolved_role,
            'department': department,
            'timezone': timezone_name,
            'status': status,
        },
    )
    return profile


def build_token_pair_for_user(user) -> dict[str, str]:
    """Mint SimpleJWT refresh and access tokens carrying safe RBAC profile claims."""
    profile = get_or_create_user_profile(user)
    refresh = RefreshToken.for_user(user)
    role = ROLE_ADMIN if user.is_superuser else profile.role
    claims = {
        'user_code': profile.user_code,
        'username': user.username,
        'email': user.email,
        'role': role,
        'department': profile.department,
    }
    for key, val in claims.items():
        refresh[key] = val
        refresh.access_token[key] = val
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def _ensure_another_active_admin_exists(target_user):
    """Prevent removing or deactivating the last active workspace Admin."""
    other_active_admins = (
        UserProfile.objects.filter(
            role=ROLE_ADMIN,
            user__is_active=True,
        )
        .exclude(status=UserProfile.AccountStatus.SUSPENDED)
        .exclude(user_id=target_user.pk)
        .exists()
    )
    other_superusers = User.objects.filter(is_superuser=True, is_active=True).exclude(
        pk=target_user.pk
    ).exists()
    if not (other_active_admins or other_superusers):
        raise ValidationError(
            {'role': ['Cannot remove or deactivate the last active workspace Admin.']}
        )


@transaction.atomic
def create_user_with_profile(
    *,
    email: str,
    password: str | None = None,
    username: str = '',
    name: str = '',
    first_name: str = '',
    last_name: str = '',
    role: str = UserProfile.Role.VIEWER,
    department: str = 'Marketing Operations',
    timezone_name: str = 'UTC',
    status: str = UserProfile.AccountStatus.ACTIVE,
    actor=None,
    source_ip: str | None = None,
    notes: str = '',
):
    """Create a Django User, associated UserProfile, and CREATE AuditLog atomically."""
    normalized_email = email.strip().lower()
    if not first_name and not last_name and name:
        first_name, last_name = split_full_name(name)

    resolved_username = derive_unique_username(normalized_email, preferred_username=username)
    is_active = status != UserProfile.AccountStatus.SUSPENDED

    user = User(
        username=resolved_username,
        email=normalized_email,
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
        is_staff=(role == ROLE_ADMIN),
    )
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()

    UserProfile.objects.create(
        user=user,
        role=role,
        department=department or 'Marketing Operations',
        timezone=timezone_name or 'UTC',
        status=status,
        last_active_at=timezone.now() if status == UserProfile.AccountStatus.ACTIVE else None,
    )
    user.refresh_from_db()

    log_account_audit(
        target_user=user,
        action=AuditLog.Action.CREATE,
        actor=actor or user,
        previous_state=None,
        new_state=serialize_user_snapshot(user),
        changed_fields=['email', 'username', 'role', 'department', 'status'],
        source_ip=source_ip,
        notes=notes or 'User account created.',
    )
    logger.info('Provisioned user %s (%s) with role=%s', user.username, user.profile.user_code, role)
    return user


@transaction.atomic
def update_user_and_profile(
    *,
    target_user,
    data: dict,
    actor=None,
    source_ip: str | None = None,
):
    """Update User and UserProfile fields while protecting the last active Admin."""
    profile = get_or_create_user_profile(target_user)
    previous_state = serialize_user_snapshot(target_user)

    next_role = data.get('role', profile.role)
    next_status = data.get('status', profile.status)
    next_is_active = data.get('is_active', target_user.is_active)
    if 'status' in data and 'is_active' not in data:
        next_is_active = next_status != UserProfile.AccountStatus.SUSPENDED
    if 'is_active' in data and not data['is_active'] and 'status' not in data:
        next_status = UserProfile.AccountStatus.SUSPENDED

    currently_active_admin = (
        (profile.role == ROLE_ADMIN or target_user.is_superuser)
        and target_user.is_active
        and profile.status != UserProfile.AccountStatus.SUSPENDED
    )
    will_remain_active_admin = (
        (next_role == ROLE_ADMIN or target_user.is_superuser)
        and next_is_active
        and next_status != UserProfile.AccountStatus.SUSPENDED
    )
    if currently_active_admin and not will_remain_active_admin:
        _ensure_another_active_admin_exists(target_user)

    changed_fields = []
    if 'name' in data and 'first_name' not in data and 'last_name' not in data:
        first_name, last_name = split_full_name(data['name'])
        data = {**data, 'first_name': first_name, 'last_name': last_name}

    user_updates = []
    for field in ('email', 'first_name', 'last_name', 'username'):
        if field in data:
            val = data[field].strip().lower() if field == 'email' else data[field].strip()
            if getattr(target_user, field) != val:
                setattr(target_user, field, val)
                user_updates.append(field)
                changed_fields.append(field)

    if target_user.is_active != next_is_active:
        target_user.is_active = next_is_active
        user_updates.append('is_active')
        changed_fields.append('is_active')

    if not target_user.is_superuser and 'role' in data:
        next_staff = next_role == ROLE_ADMIN
        if target_user.is_staff != next_staff:
            target_user.is_staff = next_staff
            user_updates.append('is_staff')

    if user_updates:
        target_user.save(update_fields=user_updates)

    profile_updates = []
    if profile.role != next_role:
        profile.role = next_role
        profile_updates.append('role')
        changed_fields.append('role')
    if profile.status != next_status:
        profile.status = next_status
        profile_updates.append('status')
        changed_fields.append('status')
    if 'department' in data and profile.department != data['department']:
        profile.department = data['department']
        profile_updates.append('department')
        changed_fields.append('department')
    if 'timezone' in data and profile.timezone != data['timezone']:
        profile.timezone = data['timezone']
        profile_updates.append('timezone')
        changed_fields.append('timezone')

    if profile_updates:
        profile_updates.append('updated_at')
        profile.save(update_fields=profile_updates)

    target_user.refresh_from_db()
    if changed_fields:
        is_status_or_role = 'role' in changed_fields or 'status' in changed_fields or 'is_active' in changed_fields
        log_account_audit(
            target_user=target_user,
            action=AuditLog.Action.STATUS_CHANGE if is_status_or_role else AuditLog.Action.UPDATE,
            actor=actor,
            previous_state=previous_state,
            new_state=serialize_user_snapshot(target_user),
            changed_fields=changed_fields,
            source_ip=source_ip,
            notes='Account updated.',
        )

    return target_user


@transaction.atomic
def deactivate_user_account(*, target_user, actor=None, source_ip: str | None = None):
    """Soft-deactivate an account and set its profile status to Suspended cleanly."""
    profile = get_or_create_user_profile(target_user)
    if profile.role == ROLE_ADMIN or target_user.is_superuser:
        _ensure_another_active_admin_exists(target_user)

    previous_state = serialize_user_snapshot(target_user)
    if target_user.is_active:
        target_user.is_active = False
        target_user.save(update_fields=['is_active'])
    if profile.status != UserProfile.AccountStatus.SUSPENDED:
        profile.status = UserProfile.AccountStatus.SUSPENDED
        profile.save(update_fields=['status', 'updated_at'])

    target_user.refresh_from_db()
    log_account_audit(
        target_user=target_user,
        action=AuditLog.Action.ARCHIVE,
        actor=actor,
        previous_state=previous_state,
        new_state=serialize_user_snapshot(target_user),
        changed_fields=['is_active', 'status'],
        source_ip=source_ip,
        notes='User soft-deactivated by administrator.',
    )
    return target_user


def validate_django_password(password: str, user=None):
    """Run configured Django password validators and convert to DRF ValidationError."""
    from django.contrib.auth.password_validation import validate_password

    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError(list(exc.messages))

