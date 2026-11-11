"""API views for JWT authentication, self-service profile, and Admin RBAC user management."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import filters, serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import UserProfile
from apps.accounts.serializers import (
    AdminCreateUserSerializer,
    AdminUpdateUserSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    RoleUpdateSerializer,
    UserAccountSerializer,
)
from apps.accounts.services import (
    build_token_pair_for_user,
    create_user_with_profile,
    deactivate_user_account,
    get_client_ip,
    get_or_create_user_profile,
    log_account_audit,
    serialize_user_snapshot,
    update_user_and_profile,
)
from apps.audit.models import AuditLog
from common.permissions import ROLE_MATRIX, IsAdminRole, is_active_account
from common.responses import success_response

User = get_user_model()


class UserAccountFilter(django_filters.FilterSet):
    """FilterSet mapping clean query parameters onto related UserProfile RBAC fields."""

    role = django_filters.CharFilter(field_name='profile__role')
    status = django_filters.CharFilter(field_name='profile__status')
    department = django_filters.CharFilter(
        field_name='profile__department',
        lookup_expr='icontains',
    )
    is_active = django_filters.BooleanFilter(field_name='is_active')

    class Meta:
        model = User
        fields = ['role', 'status', 'department', 'is_active']


class RegisterView(APIView):
    """Public self-registration endpoint issuing JWT tokens for Viewer/Analyst accounts."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Auth'],
        summary='Register Workspace User',
        request=RegisterSerializer,
        responses={201: UserAccountSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = create_user_with_profile(
            email=data['email'],
            password=data['password'],
            username=data.get('username', ''),
            name=data.get('name', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            role=data.get('role', UserProfile.Role.VIEWER),
            department=data.get('department', 'Marketing Operations'),
            timezone_name=data.get('timezone', 'UTC'),
            status=UserProfile.AccountStatus.ACTIVE,
            source_ip=get_client_ip(request),
            notes='Self-registered via /api/v1/auth/register/.',
        )
        tokens = build_token_pair_for_user(user)
        return success_response(
            data={
                'user': UserAccountSerializer(user).data,
                **tokens,
            },
            message='Account registered successfully.',
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Authenticates via email or username and issues SimpleJWT access/refresh tokens."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Auth'],
        summary='Sign In (JWT Login)',
        request=LoginSerializer,
        responses={200: UserAccountSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        user = payload['user']
        return success_response(
            data={
                'user': UserAccountSerializer(user).data,
                'access': payload['access'],
                'refresh': payload['refresh'],
            },
            message='Signed in successfully.',
            status_code=status.HTTP_200_OK,
        )


@extend_schema(tags=['Auth'], summary='Refresh JWT Access Token')
class CustomTokenRefreshView(TokenRefreshView):
    """SimpleJWT token refresh endpoint with automatic refresh token rotation."""


class LogoutView(APIView):
    """Blacklists the caller's JWT refresh token and logs sign-out in AuditLog."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        summary='Sign Out & Revoke Refresh Token',
        request=LogoutSerializer,
        responses={200: dict},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        log_account_audit(
            target_user=request.user,
            action=AuditLog.Action.STATUS_CHANGE,
            actor=request.user,
            previous_state=serialize_user_snapshot(request.user),
            new_state=serialize_user_snapshot(request.user),
            changed_fields=[],
            source_ip=get_client_ip(request),
            notes='User logged out and refresh token blacklisted.',
        )
        return success_response(
            data=None,
            message='Signed out successfully.',
            status_code=status.HTTP_200_OK,
        )


class MeProfileView(APIView):
    """Authenticated user's own profile read and non-privileged metadata update."""

    permission_classes = [IsAuthenticated]

    def _ensure_active(self, request):
        if not is_active_account(request.user):
            return False
        get_or_create_user_profile(request.user)
        return True

    @extend_schema(
        tags=['Auth'],
        summary='Get Current User Profile',
        responses={200: UserAccountSerializer},
    )
    def get(self, request):
        if not self._ensure_active(request):
            return Response(
                {'detail': 'Workspace account is suspended or inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return success_response(
            data=UserAccountSerializer(request.user).data,
            message='Current user profile loaded.',
        )

    @extend_schema(
        tags=['Auth'],
        summary='Update Current User Profile',
        request=ProfileUpdateSerializer,
        responses={200: UserAccountSerializer},
    )
    def patch(self, request):
        if not self._ensure_active(request):
            return Response(
                {'detail': 'Workspace account is suspended or inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProfileUpdateSerializer(
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        updated_user = update_user_and_profile(
            target_user=request.user,
            data=serializer.validated_data,
            actor=request.user,
            source_ip=get_client_ip(request),
        )
        return success_response(
            data=UserAccountSerializer(updated_user).data,
            message='Profile updated successfully.',
        )


class ChangePasswordView(APIView):
    """Allows an authenticated active user to rotate their own password."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        summary='Change Current User Password',
        request=ChangePasswordSerializer,
        responses={200: dict},
    )
    def post(self, request):
        if not is_active_account(request.user):
            return Response(
                {'detail': 'Workspace account is suspended or inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])

        log_account_audit(
            target_user=request.user,
            action=AuditLog.Action.UPDATE,
            actor=request.user,
            previous_state=None,
            new_state=serialize_user_snapshot(request.user),
            changed_fields=['password'],
            source_ip=get_client_ip(request),
            notes='User changed own password.',
        )
        return success_response(
            data=None,
            message='Password updated successfully.',
        )


class ForgotPasswordView(APIView):
    """Non-enumerating password reset request generating signed uid/token email."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Auth'],
        summary='Request Password Reset Link',
        request=ForgotPasswordSerializer,
        responses={200: dict},
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_mail(
                subject='AttributionIQ Password Reset Request',
                message=(
                    'Use the following reset credentials to set a new password:\n'
                    f'uid: {uid}\ntoken: {token}\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

        return success_response(
            data=None,
            message='If an active account matches that email, password reset instructions have been dispatched.',
        )


class ResetPasswordView(APIView):
    """Validates uidb64 and signed reset token to set a new password."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Auth'],
        summary='Confirm Password Reset',
        request=ResetPasswordSerializer,
        responses={200: dict},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])

        log_account_audit(
            target_user=user,
            action=AuditLog.Action.UPDATE,
            actor=user,
            previous_state=None,
            new_state=serialize_user_snapshot(user),
            changed_fields=['password'],
            source_ip=get_client_ip(request),
            notes='Password reset completed via token verification.',
        )
        return success_response(
            data=None,
            message='Password has been reset successfully.',
        )


class RoleMatrixView(APIView):
    """Returns canonical RBAC roles and permission capabilities for UI/client inspection."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        summary='List Canonical RBAC Role Definitions',
        responses={
            200: inline_serializer(
                name='RoleDefinitionItem',
                fields={
                    'role': drf_serializers.CharField(),
                    'description': drf_serializers.CharField(),
                    'capabilities': drf_serializers.ListField(child=drf_serializers.CharField()),
                },
                many=True,
            )
        },
    )
    def get(self, request):
        if not is_active_account(request.user):
            return Response(
                {'detail': 'Workspace account is suspended or inactive.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return success_response(
            data=ROLE_MATRIX,
            message='RBAC role definitions retrieved.',
        )


@extend_schema_view(
    list=extend_schema(tags=['Users'], summary='List Workspace Users (Admin)'),
    retrieve=extend_schema(tags=['Users'], summary='Get Workspace User Detail (Admin)'),
    create=extend_schema(tags=['Users'], summary='Provision / Invite Workspace User (Admin)'),
    partial_update=extend_schema(tags=['Users'], summary='Update Workspace User (Admin)'),
    update=extend_schema(tags=['Users'], summary='Replace Workspace User Metadata (Admin)'),
    destroy=extend_schema(tags=['Users'], summary='Soft-Deactivate Workspace User (Admin)'),
)
class UserManagementViewSet(viewsets.ModelViewSet):
    """Admin-only user directory, invitation/provisioning, RBAC assignment, and soft-deactivation."""

    queryset = User.objects.select_related('profile').order_by('id')
    serializer_class = UserAccountSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = UserAccountFilter
    search_fields = ['username', 'email', 'first_name', 'last_name', 'profile__user_code']
    ordering_fields = ['id', 'username', 'email', 'date_joined', 'last_login']
    ordering = ['id']

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateUserSerializer
        if self.action in ('update', 'partial_update'):
            return AdminUpdateUserSerializer
        if self.action == 'update_role':
            return RoleUpdateSerializer
        return UserAccountSerializer

    def create(self, request, *args, **kwargs):
        serializer = AdminCreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = create_user_with_profile(
            email=data['email'],
            password=data.get('password') or None,
            username=data.get('username', ''),
            name=data.get('name', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            role=data.get('role', UserProfile.Role.VIEWER),
            department=data.get('department', 'Marketing Operations'),
            timezone_name=data.get('timezone', 'UTC'),
            status=data.get('status', UserProfile.AccountStatus.ACTIVE),
            actor=request.user,
            source_ip=get_client_ip(request),
            notes='Provisioned by Admin via /api/v1/users/.',
        )
        return success_response(
            data=UserAccountSerializer(user).data,
            message='User provisioned successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        target_user = self.get_object()
        serializer = AdminUpdateUserSerializer(
            data=request.data,
            partial=partial,
            context={'target_user': target_user},
        )
        serializer.is_valid(raise_exception=True)
        updated_user = update_user_and_profile(
            target_user=target_user,
            data=serializer.validated_data,
            actor=request.user,
            source_ip=get_client_ip(request),
        )
        return success_response(
            data=UserAccountSerializer(updated_user).data,
            message='User updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        target_user = self.get_object()
        deactivated = deactivate_user_account(
            target_user=target_user,
            actor=request.user,
            source_ip=get_client_ip(request),
        )
        return success_response(
            data=UserAccountSerializer(deactivated).data,
            message='User soft-deactivated successfully.',
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Users'],
        summary='Assign RBAC Role to User (Admin)',
        request=RoleUpdateSerializer,
        responses={200: UserAccountSerializer},
    )
    @action(detail=True, methods=['patch'], url_path='role')
    def update_role(self, request, pk=None):
        target_user = self.get_object()
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_user = update_user_and_profile(
            target_user=target_user,
            data={'role': serializer.validated_data['role']},
            actor=request.user,
            source_ip=get_client_ip(request),
        )
        return success_response(
            data=UserAccountSerializer(updated_user).data,
            message='User role updated successfully.',
        )
