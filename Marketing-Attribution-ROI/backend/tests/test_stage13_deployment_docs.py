"""Stage 13 deployment, configuration, Docker & documentation deliverable verification tests."""

import importlib
from pathlib import Path

from django.conf import settings
from django.test import override_settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / 'backend'
FRONTEND_DIR = PROJECT_ROOT / 'frontend'


def test_stage13_docker_env_and_documentation_deliverables_exist():
    required_files = [
        PROJECT_ROOT / 'README.md',
        PROJECT_ROOT / 'docker-compose.yml',
        PROJECT_ROOT / 'database' / 'init_mysql.sql',
        PROJECT_ROOT / 'database' / 'schema_documentation.md',
        PROJECT_ROOT / 'docs' / 'API_DOCUMENTATION.md',
        PROJECT_ROOT / 'docs' / 'ATTRIBUTION_LOGIC.md',
        PROJECT_ROOT / 'docs' / 'DATA_DICTIONARY.md',
        PROJECT_ROOT / 'docs' / 'DATABASE_DESIGN.md',
        PROJECT_ROOT / 'docs' / 'SETUP_GUIDE.md',
        BACKEND_DIR / '.env.example',
        BACKEND_DIR / 'Dockerfile',
        BACKEND_DIR / '.dockerignore',
        BACKEND_DIR / 'requirements.txt',
        FRONTEND_DIR / '.env.example',
        FRONTEND_DIR / 'Dockerfile',
        FRONTEND_DIR / 'nginx.conf',
    ]
    for fpath in required_files:
        assert fpath.is_file(), f'Missing deliverable file: {fpath}'
        assert fpath.stat().st_size > 0, f'Empty deliverable file: {fpath}'

    requirements_text = (BACKEND_DIR / 'requirements.txt').read_text(encoding='utf-8')
    assert 'gunicorn' in requirements_text.lower()

    compose_text = (PROJECT_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    assert 'services:' in compose_text
    assert 'backend:' in compose_text
    assert 'frontend:' in compose_text
    assert 'db:' in compose_text
    assert '/api/v1/health/' in compose_text

    dockerfile_text = (BACKEND_DIR / 'Dockerfile').read_text(encoding='utf-8')
    assert 'gunicorn config.wsgi:application' in dockerfile_text

    frontend_env = (FRONTEND_DIR / '.env.example').read_text(encoding='utf-8')
    assert 'http://localhost:8000/api/v1' in frontend_env
    assert 'VITE_USE_MOCK_DATA' in frontend_env


def test_stage13_production_settings_hardening():
    prod_mod = importlib.import_module('config.settings_prod')
    assert prod_mod.ENVIRONMENT == 'production'
    assert prod_mod.DEBUG is False
    assert prod_mod.SESSION_COOKIE_SECURE is True
    assert prod_mod.CSRF_COOKIE_SECURE is True
    assert prod_mod.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert prod_mod.X_FRAME_OPTIONS == 'DENY'
    assert 'gunicorn' in (BACKEND_DIR / 'requirements.txt').read_text(encoding='utf-8').lower()
    assert hasattr(settings, 'ATTRIBUTION_SETTINGS')
    with override_settings(DEBUG=False):
        assert prod_mod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True

