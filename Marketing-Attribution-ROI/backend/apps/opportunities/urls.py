"""URL routes for Sales Opportunities API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.opportunities.views import OpportunityViewSet

router = DefaultRouter()
router.register(r'', OpportunityViewSet, basename='opportunities')

urlpatterns = [
    path('', include(router.urls)),
]

