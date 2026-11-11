"""Serializers for JWT authentication, registration, profile management, and Admin RBAC."""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserProfile
from apps.accounts.services import (
    build_token_pair_for_user,
    get_or_create_user_profile,
    validate_django_password,
)
from common.permissions import ROLE_ADMIN

User = get_user_model()

SELF_REGISTER_ALLOWED_ROLES = (
    UserProfile.Role.VIEWER,
    UserProfile.Role.MARKETING_ANALYST,
)


class UserAccountSerializer(serializers.ModelSerializer):
    """Read serializer combining Django User and UserProfile RBAC fields."""

    user_code = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    last_active_at = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'user_code',
            'username',
            'email',
            'first_name',
            'last_name',
            'name',
            'role',
            'department',
            'timezone',
            'status',
            'is_active',
            'last_login',
            'last_active_at',
            'date_joined',
        ]
        read_only_fields = fields

    def _profile(self, obj):
        return getattr(obj, 'profile', None)

    def get_user_code(self, obj) -> str:
        profile = self._profile(obj)
        return profile.user_code if profile else ''

    def get_name(self, obj) -> str:
        full_name = obj.get_full_name().strip()
        return full_name or obj.username

    def get_role(self, obj) -> str:
        if obj.is_superuser:
            return ROLE_ADMIN
        profile = self._profile(obj)
        return profile.role if profile else UserProfile.Role.VIEWER

    def get_department(self, obj) -> str:
        profile = self._profile(obj)
        return profile.department if profile else 'Marketing Operations'

    def get_timezone(self, obj) -> str:
        profile = self._profile(obj)
        return profile.timezone if profile else 'UTC'

    def get_status(self, obj) -> str:
        profile = self._profile(obj)
        return profile.status if profile else UserProfile.AccountStatus.ACTIVE

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_last_active_at(self, obj) -> datetime | None:
        profile = self._profile(obj)
        return profile.last_active_at if profile else None


class RegisterSerializer(serializers.Serializer):
    """Public self-registration serializer blocking privileged role escalation."""

    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=UserProfile.Role.choices,
        default=UserProfile.Role.VIEWER,
        required=False,
    )
    department = serializers.CharField(max_length=100, required=False, default='Marketing Operations')
    timezone = serializers.CharField(max_length=64, required=False, default='UTC')

    def validate_email(self, value: str) -> str:
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return normalized

    def validate_username(self, value: str) -> str:
        cleaned = value.strip()
        if cleaned and User.objects.filter(username__iexact=cleaned).exists():
            raise serializers.ValidationError('This username is already taken.')
        return cleaned

    def validate_role(self, value: str) -> str:
        if value not in SELF_REGISTER_ALLOWED_ROLES:
            raise serializers.ValidationError(
                'Self-registration is restricted to Viewer or Marketing Analyst roles. '
                'Admin or Marketing Manager roles must be assigned by an administrator.'
            )
        return value

    def validate_password(self, value: str) -> str:
        validate_django_password(value)
        return value

    def validate(self, attrs):
        confirm = attrs.pop('confirm_password', None)
        if confirm is not None and confirm != '' and confirm != attrs['password']:
            raise serializers.ValidationError({'confirm_password': ['Passwords do not match.']})
        return attrs


class LoginSerializer(serializers.Serializer):
    """Authenticates via email or username and returns SimpleJWT access/refresh tokens."""

    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        username = (attrs.get('username') or '').strip()
        password = attrs.get('password') or ''

        identifier = email or username
        if not identifier:
            raise serializers.ValidationError(
                {'non_field_errors': ['Provide either email or username to sign in.']}
            )

        user = None
        if email:
            user = User.objects.select_related('profile').filter(email__iexact=email).first()
        if user is None and username:
            user = User.objects.select_related('profile').filter(username__iexact=username).first()
        if user is None and email and '@' not in email:
            user = User.objects.select_related('profile').filter(username__iexact=email).first()

        if user is None or not user.check_password(password):
            raise serializers.ValidationError(
                {'non_field_errors': ['Invalid credentials. Please verify email/username and password.']}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {'non_field_errors': ['This user account has been deactivated.']}
            )

        profile = get_or_create_user_profile(user)
        if profile.status == UserProfile.AccountStatus.SUSPENDED:
            raise serializers.ValidationError(
                {'non_field_errors': ['This workspace account is currently suspended.']}
            )

        now = timezone.now()
        user.last_login = now
        user.save(update_fields=['last_login'])
        profile.last_active_at = now
        if profile.status == UserProfile.AccountStatus.INVITED:
            profile.status = UserProfile.AccountStatus.ACTIVE
            profile.save(update_fields=['last_active_at', 'status', 'updated_at'])
        else:
            profile.save(update_fields=['last_active_at', 'updated_at'])

        tokens = build_token_pair_for_user(user)
        return {
            'user': user,
            **tokens,
        }


class LogoutSerializer(serializers.Serializer):
    """Validates and blacklists a SimpleJWT refresh token on logout."""

    refresh = serializers.CharField()

    def validate(self, attrs):
        token_str = attrs['refresh']
        try:
            token = RefreshToken(token_str)
            token.blacklist()
        except TokenError as exc:
            raise serializers.ValidationError({'refresh': [f'Invalid or expired refresh token: {exc}']})
        return attrs


class ProfileUpdateSerializer(serializers.Serializer):
    """Allows authenticated users to update personal profile metadata (never role/status)."""

    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    department = serializers.CharField(max_length=100, required=False)
    timezone = serializers.CharField(max_length=64, required=False)

    def validate_email(self, value: str) -> str:
        normalized = value.strip().lower()
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        qs = User.objects.filter(email__iexact=normalized)
        if user and user.pk:
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise serializers.ValidationError('Another account already uses this email address.')
        return normalized


class ChangePasswordSerializer(serializers.Serializer):
    """Validates current password before applying a validated new password."""

    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=6, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_current_password(self, value: str) -> str:
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value: str) -> str:
        validate_django_password(value, user=self.context['request'].user)
        return value

    def validate(self, attrs):
        confirm = attrs.get('confirm_password')
        if confirm is not None and confirm != '' and confirm != attrs['new_password']:
            raise serializers.ValidationError({'confirm_password': ['Passwords do not match.']})
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': ['New password must differ from current password.']}
            )
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Initiates non-enumerating password reset request by email."""

    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """Completes password reset using Django uidb64 and signed reset token."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=6, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=user_id, is_active=True)
        except Exception as exc:
            raise serializers.ValidationError({'uid': ['Invalid password reset user identifier.']}) from exc

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'token': ['Invalid or expired password reset token.']})

        validate_django_password(attrs['new_password'], user=user)

        confirm = attrs.get('confirm_password')
        if confirm is not None and confirm != '' and confirm != attrs['new_password']:
            raise serializers.ValidationError({'confirm_password': ['Passwords do not match.']})

        attrs['user'] = user
        return attrs


class AdminCreateUserSerializer(serializers.Serializer):
    """Admin serializer for provisioning/inviting team members with explicit RBAC roles."""

    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=UserProfile.Role.choices, default=UserProfile.Role.VIEWER)
    department = serializers.CharField(max_length=100, required=False, default='Marketing Operations')
    timezone = serializers.CharField(max_length=64, required=False, default='UTC')
    status = serializers.ChoiceField(
        choices=UserProfile.AccountStatus.choices,
        default=UserProfile.AccountStatus.ACTIVE,
        required=False,
    )

    def validate_email(self, value: str) -> str:
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError('A user with this email address already exists.')
        return normalized

    def validate_username(self, value: str) -> str:
        cleaned = value.strip()
        if cleaned and User.objects.filter(username__iexact=cleaned).exists():
            raise serializers.ValidationError('This username is already taken.')
        return cleaned

    def validate_password(self, value: str) -> str:
        if value:
            validate_django_password(value)
        return value


class AdminUpdateUserSerializer(serializers.Serializer):
    """Admin serializer to edit user metadata, RBAC role, department, and active status."""

    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    role = serializers.ChoiceField(choices=UserProfile.Role.choices, required=False)
    department = serializers.CharField(max_length=100, required=False)
    timezone = serializers.CharField(max_length=64, required=False)
    status = serializers.ChoiceField(choices=UserProfile.AccountStatus.choices, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate_email(self, value: str) -> str:
        normalized = value.strip().lower()
        target_user = self.context.get('target_user')
        qs = User.objects.filter(email__iexact=normalized)
        if target_user and target_user.pk:
            qs = qs.exclude(pk=target_user.pk)
        if qs.exists():
            raise serializers.ValidationError('Another user already owns this email address.')
        return normalized


class RoleUpdateSerializer(serializers.Serializer):
    """Dedicated payload for Admin role assignment changes."""

    role = serializers.ChoiceField(choices=UserProfile.Role.choices)
