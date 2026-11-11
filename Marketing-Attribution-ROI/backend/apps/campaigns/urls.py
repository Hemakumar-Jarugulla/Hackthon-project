"""URL routes for Marketing Campaigns API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.campaigns.views import CampaignViewSet

router = DefaultRouter()
router.register(r'', CampaignViewSet, basename='campaigns')

urlpatterns = [
    path('', include(router.urls)),
]

