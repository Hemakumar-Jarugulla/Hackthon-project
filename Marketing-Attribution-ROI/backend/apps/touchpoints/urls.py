"""URL routes for Marketing Touchpoints API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.touchpoints.views import TouchpointViewSet

router = DefaultRouter()
router.register(r'', TouchpointViewSet, basename='touchpoints')

urlpatterns = [
    path('', include(router.urls)),
]

