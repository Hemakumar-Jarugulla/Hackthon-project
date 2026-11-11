"""Role constants and base DRF permission classes for RBAC enforcement."""

from rest_framework.permissions import BasePermission, SAFE_METHODS

ROLE_ADMIN = 'Admin'
ROLE_MARKETING_MANAGER = 'Marketing Manager'
ROLE_MARKETING_ANALYST = 'Marketing Analyst'
ROLE_VIEWER = 'Viewer'

ALL_ROLES = (
    ROLE_ADMIN,
    ROLE_MARKETING_MANAGER,
    ROLE_MARKETING_ANALYST,
    ROLE_VIEWER,
)

ROLE_MATRIX = [
    {
        'role': ROLE_ADMIN,
        'description': (
            'Full administrative control across user roles, campaigns, costs, '
            'attribution runs, exception resolution, validation, and data generation.'
        ),
        'capabilities': [
            'users:manage',
            'campaigns:write',
            'costs:write',
            'attribution:run',
            'exceptions:resolve',
            'validation:run',
            'analytics:read',
        ],
    },
    {
        'role': ROLE_MARKETING_MANAGER,
        'description': (
            'Create and manage campaigns, channels, creatives, audiences, '
            'lead/opportunity updates, marketing costs, and analytics.'
        ),
        'capabilities': [
            'campaigns:write',
            'costs:write',
            'attribution:run',
            'validation:run',
            'analytics:read',
        ],
    },
    {
        'role': ROLE_MARKETING_ANALYST,
        'description': (
            'Execute attribution comparisons, triage data exceptions, run validation checks, '
            'and export ROI intelligence reports.'
        ),
        'capabilities': [
            'attribution:run',
            'exceptions:resolve',
            'validation:run',
            'analytics:read',
        ],
    },
    {
        'role': ROLE_VIEWER,
        'description': (
            'Read-only access to dashboards, attribution outputs, ROI metrics, '
            'and executive reports.'
        ),
        'capabilities': [
            'analytics:read',
        ],
    },
]


def is_active_account(user) -> bool:
    """Verify user is authenticated, active, and not suspended at profile level."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    profile = getattr(user, 'profile', None)
    if profile is not None and profile.status == 'Suspended':
        return False
    return True


def _get_user_role(user):
    """Resolve RBAC role from attached UserProfile or fallback attribute."""
    if not is_active_account(user):
        return None
    if user.is_superuser:
        return ROLE_ADMIN
    profile = getattr(user, 'profile', None)
    if profile is not None:
        return profile.role
    return getattr(user, 'role', ROLE_VIEWER)


class HasRolePermission(BasePermission):
    """Base permission checking whether the authenticated user holds an allowed role."""

    allowed_roles = ()

    def has_permission(self, request, view):
        if not is_active_account(request.user):
            return False
        return _get_user_role(request.user) in self.allowed_roles


class IsActiveUser(BasePermission):
    """Allows read/analytics access to any authenticated, non-suspended user."""

    def has_permission(self, request, view):
        return is_active_account(request.user)


class IsAdminRole(HasRolePermission):
    """Allows access strictly to Admin users or superusers."""

    allowed_roles = (ROLE_ADMIN,)


class IsManagerOrAdmin(HasRolePermission):
    """Allows create/update/archive operations for Admin and Marketing Manager roles."""

    allowed_roles = (ROLE_ADMIN, ROLE_MARKETING_MANAGER)


class IsAnalystOrAbove(HasRolePermission):
    """Allows analytical execution (attribution/validation) for Analysts, Managers, and Admins."""

    allowed_roles = (ROLE_ADMIN, ROLE_MARKETING_MANAGER, ROLE_MARKETING_ANALYST)


class ReadOnlyOrManagerWrite(BasePermission):
    """Authenticated active users may read; only Admin or Marketing Manager may mutate."""

    def has_permission(self, request, view):
        if not is_active_account(request.user):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _get_user_role(request.user) in (ROLE_ADMIN, ROLE_MARKETING_MANAGER)


class IsAdminOrSelf(BasePermission):
    """Allows Admins full object access or a user to inspect/edit their own record."""

    def has_permission(self, request, view):
        return is_active_account(request.user)

    def has_object_permission(self, request, view, obj):
        if not is_active_account(request.user):
            return False
        if _get_user_role(request.user) == ROLE_ADMIN:
            return True
        target_user = getattr(obj, 'user', obj)
        return getattr(target_user, 'pk', None) == request.user.pk
