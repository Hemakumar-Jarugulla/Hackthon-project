"""Stage 1 verification tests covering configuration, utilities, health, and OpenAPI schema."""

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.test import override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from common.exceptions import custom_exception_handler
from common.utils import format_deterministic_id, safe_divide


@pytest.mark.django_db
def test_django_system_check_passes():
    call_command('check')


@pytest.mark.django_db
def test_health_endpoint_returns_healthy():
    client = APIClient()
    response = client.get('/api/v1/health/')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'healthy'
    assert body['service'] == 'AttributionIQ Backend API'
    assert body['api_prefix'] == '/api/v1/'
    assert body['database']['connected'] is True
    assert body['attribution_defaults']['DEFAULT_MODEL'] == 'position_based'


@pytest.mark.django_db
def test_openapi_schema_and_swagger_ui_serve():
    client = APIClient()
    schema_resp = client.get('/api/schema/')
    assert schema_resp.status_code == 200

    docs_resp = client.get('/api/docs/')
    assert docs_resp.status_code == 200
    assert b'swagger-ui' in docs_resp.content


def test_root_redirects_to_api_docs():
    response = APIClient().get('/')
    assert response.status_code == 302
    assert response['Location'] == '/api/docs/'


def test_safe_divide_handles_zero_and_none():
    assert safe_divide(Decimal('100'), Decimal('0')) is None
    assert safe_divide(100, 0, default=Decimal('0')) == Decimal('0')
    assert safe_divide(None, 50) is None
    assert safe_divide(150, 50) == Decimal('3')


def test_format_deterministic_id_matches_platform_spec():
    assert format_deterministic_id('CMP', 2026, 1) == 'CMP-2026-000001'
    assert format_deterministic_id('SES', 2026, 42) == 'SES-2026-000042'


def test_custom_exception_handler_formats_drf_errors():
    exc = ValidationError({'name': ['Campaign name is required.']})
    response = custom_exception_handler(exc, {'view': None})
    assert response.status_code == 400
    assert response.data['success'] is False
    assert response.data['error']['code'] == 'invalid'
    assert 'name' in response.data['error']['details']


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
def test_cors_allows_vite_frontend_origin():
    from django.conf import settings

    assert 'http://localhost:5173' in settings.CORS_ALLOWED_ORIGINS
