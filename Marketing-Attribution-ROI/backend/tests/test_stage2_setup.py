"""Stage 2 verification tests covering app registration and MySQL database config."""

import pytest
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from rest_framework.test import APIClient

from common.db import build_database_config

EXPECTED_LOCAL_APPS = [
    'accounts',
    'channels',
    'campaigns',
    'creatives',
    'audiences',
    'contacts',
    'web_sessions',
    'touchpoints',
    'leads',
    'opportunities',
    'orders',
    'costs',
    'attribution',
    'analytics',
    'exceptions',
    'audit',
    'validation',
    'data_generator',
]


def test_all_domain_and_generator_apps_registered():
    loaded_labels = {cfg.label for cfg in apps.get_app_configs()}
    for label in EXPECTED_LOCAL_APPS:
        assert label in loaded_labels, f'Expected app "{label}" to be registered'
    assert len(settings.LOCAL_APPS) == 18


def test_mysql_database_config_builder_sets_strict_utf8mb4():
    cfg = build_database_config(
        base_dir=settings.BASE_DIR,
        engine='mysql',
        name='attribution_iq',
        user='attribution_user',
        password='secret',
        host='127.0.0.1',
        port='3306',
        conn_max_age=120,
    )
    assert cfg['ENGINE'] == 'django.db.backends.mysql'
    assert cfg['NAME'] == 'attribution_iq'
    assert cfg['USER'] == 'attribution_user'
    assert cfg['HOST'] == '127.0.0.1'
    assert cfg['PORT'] == '3306'
    assert cfg['CONN_MAX_AGE'] == 120
    assert cfg['OPTIONS']['charset'] == 'utf8mb4'
    assert "STRICT_TRANS_TABLES" in cfg['OPTIONS']['init_command']


@pytest.mark.django_db
def test_check_db_management_command_runs_cleanly():
    call_command('check_db')


@pytest.mark.django_db
def test_no_pending_migrations_in_stage2():
    call_command('makemigrations', '--check', '--dry-run')


@pytest.mark.django_db
def test_health_endpoint_reports_registered_apps_and_db_diagnostics():
    client = APIClient()
    response = client.get('/api/v1/health/')
    assert response.status_code == 200
    body = response.json()
    assert body['registered_apps_count'] == 18
    assert body['database']['connected'] is True
    assert 'database' in body['database']
    assert 'server_version' in body['database']

