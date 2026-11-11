"""URL routes for Marketing Creatives API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.creatives.views import CreativeViewSet

router = DefaultRouter()
router.register(r'', CreativeViewSet, basename='creatives')

urlpatterns = [
    path('', include(router.urls)),
]

