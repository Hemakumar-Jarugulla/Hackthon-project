"""URL routes for Multi-Touch Attribution Engine and Models APIs."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.attribution.views import (
    AttributionCompareView,
    AttributionExecuteView,
    AttributionModelViewSet,
    AttributionResultViewSet,
    AttributionRunViewSet,
)

router = DefaultRouter()
router.register(r'models', AttributionModelViewSet, basename='attribution-models')
router.register(r'runs', AttributionRunViewSet, basename='attribution-runs')
router.register(r'results', AttributionResultViewSet, basename='attribution-results')

urlpatterns = [
    path('run/', AttributionExecuteView.as_view(), name='attribution-run'),
    path('calculate/', AttributionExecuteView.as_view(), name='attribution-calculate'),
    path('compare/', AttributionCompareView.as_view(), name='attribution-compare'),
    path('', include(router.urls)),
]

