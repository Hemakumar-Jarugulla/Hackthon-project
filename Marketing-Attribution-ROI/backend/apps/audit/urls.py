"""URL routes for Audit Log inspection endpoints."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.audit.views import AuditLogViewSet

router = DefaultRouter()
router.register(r'', AuditLogViewSet, basename='audit-logs')

urlpatterns = [
    path('', include(router.urls)),
]

