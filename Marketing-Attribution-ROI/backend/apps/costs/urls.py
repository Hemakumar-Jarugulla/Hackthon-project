"""URL routes for Marketing Costs API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.costs.views import CostRecordViewSet

router = DefaultRouter()
router.register(r'', CostRecordViewSet, basename='costs')

urlpatterns = [
    path('', include(router.urls)),
]

