"""URL routes for Web Sessions API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.web_sessions.views import WebSessionViewSet

router = DefaultRouter()
router.register(r'', WebSessionViewSet, basename='sessions')

urlpatterns = [
    path('', include(router.urls)),
]

