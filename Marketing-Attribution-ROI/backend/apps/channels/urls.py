"""URL routes for Marketing Channels API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.channels.views import ChannelViewSet

router = DefaultRouter()
router.register(r'', ChannelViewSet, basename='channels')

urlpatterns = [
    path('', include(router.urls)),
]

