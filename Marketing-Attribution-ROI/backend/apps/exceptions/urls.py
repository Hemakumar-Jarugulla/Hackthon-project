"""URL routes for Data Quality Exceptions API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.exceptions.views import DataExceptionViewSet

router = DefaultRouter()
router.register(r'', DataExceptionViewSet, basename='exceptions')

urlpatterns = [
    path('', include(router.urls)),
]

