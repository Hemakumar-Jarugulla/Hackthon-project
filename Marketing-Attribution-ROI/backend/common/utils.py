"""Common utility helpers and Stage 1/2 health-check endpoint."""

from datetime import datetime, timezone
from decimal import Decimal

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import get_database_status


def safe_divide(numerator, denominator, default=None):
    """
    Safely divide two numbers without raising ZeroDivisionError.
    Returns `default` (typically `None`) when denominator is zero or missing.
    """
    if numerator is None or denominator is None:
        return default
    denom = Decimal(str(denominator))
    if denom == 0:
        return default
    return Decimal(str(numerator)) / denom


def format_deterministic_id(prefix, year, sequence, width=6):
    """Format deterministic domain identifiers such as CMP-2026-000001."""
    return f'{prefix}-{year}-{int(sequence):0{width}d}'


class HealthCheckView(APIView):
    """Public health-check endpoint verifying Django API and database readiness."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary='API Health Check',
        description='Returns service health, active database engine status, and API defaults.',
        responses={200: dict},
    )
    def get(self, request):
        db_status = get_database_status()
        http_status = (
            status.HTTP_200_OK
            if db_status['connected']
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        payload = {
            'status': 'healthy' if db_status['connected'] else 'degraded',
            'service': 'AttributionIQ Backend API',
            'version': '1.0.0',
            'environment': settings.ENVIRONMENT,
            'api_prefix': '/api/v1/',
            'registered_apps_count': len(settings.LOCAL_APPS),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': db_status,
            'attribution_defaults': settings.ATTRIBUTION_SETTINGS,
        }
        return Response(payload, status=http_status)

