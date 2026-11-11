"""URL routes for Data Validation APIs."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.validation.views import (
    ValidationReportView,
    ValidationRunView,
    ValidationRunViewSet,
)

router = DefaultRouter()
router.register(r'runs', ValidationRunViewSet, basename='validation-runs')

urlpatterns = [
    path('run/', ValidationRunView.as_view(), name='validation-run'),
    path('report/', ValidationReportView.as_view(), name='validation-report'),
    path('', include(router.urls)),
]

