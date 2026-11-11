"""URL routes for Target Audiences API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.audiences.views import AudienceViewSet

router = DefaultRouter()
router.register(r'', AudienceViewSet, basename='audiences')

urlpatterns = [
    path('', include(router.urls)),
]

