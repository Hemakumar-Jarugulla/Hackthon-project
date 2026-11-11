"""URL routing for JWT Authentication and Admin RBAC User Management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    ChangePasswordView,
    CustomTokenRefreshView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeProfileView,
    RegisterView,
    ResetPasswordView,
    RoleMatrixView,
    UserManagementViewSet,
)

users_router = DefaultRouter()
users_router.register(r'', UserManagementViewSet, basename='users')

auth_urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeProfileView.as_view(), name='auth-me'),
    path('profile/', MeProfileView.as_view(), name='auth-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='auth-reset-password'),
    path('roles/', RoleMatrixView.as_view(), name='auth-roles'),
]

users_urlpatterns = [
    path('', include(users_router.urls)),
]

