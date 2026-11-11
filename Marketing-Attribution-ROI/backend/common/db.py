"""Database configuration builder and live connection diagnostics helpers."""

from pathlib import Path

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError


def build_database_config(
    *,
    base_dir: Path,
    engine: str,
    name: str,
    user: str = 'root',
    password: str = '',
    host: str = '127.0.0.1',
    port: str = '3306',
    conn_max_age: int = 60,
):
    """
    Build Django's DATABASES['default'] configuration from environment parameters.
    Supports MySQL (utf8mb4 + strict SQL mode) and SQLite fallback.
    """
    normalized = (engine or '').strip().lower()
    if normalized in ('mysql', 'django.db.backends.mysql'):
        return {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': name,
            'USER': user,
            'PASSWORD': password,
            'HOST': host,
            'PORT': str(port),
            'CONN_MAX_AGE': conn_max_age,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }

    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': base_dir / name,
    }


def get_database_status(alias='default'):
    """
    Test database connectivity safely and return structured diagnostics
    including active engine, target database name, server version, and errors.
    """
    db_cfg = settings.DATABASES[alias]
    engine = db_cfg['ENGINE'].rsplit('.', 1)[-1]
    db_name = str(db_cfg.get('NAME', ''))
    if engine == 'sqlite3':
        db_name = Path(db_name).name

    connected = True
    server_version = None
    error_message = None

    try:
        conn = connections[alias]
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION()' if engine == 'mysql' else 'SELECT sqlite_version()')
            row = cursor.fetchone()
            server_version = row[0] if row else None
    except OperationalError as exc:
        connected = False
        error_message = str(exc)

    return {
        'engine': engine,
        'database': db_name,
        'host': db_cfg.get('HOST') or 'local-file',
        'port': str(db_cfg.get('PORT') or ''),
        'connected': connected,
        'server_version': server_version,
        'error': error_message,
    }

