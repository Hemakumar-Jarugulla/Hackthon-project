"""
Django settings for the Marketing Attribution & ROI Intelligence Platform backend.

Stage 1 initializes core Django, DRF, JWT defaults, CORS, OpenAPI (drf-spectacular),
structured Python logging, and environment loading. Stage 2 switches the active
database connection to MySQL and registers modular domain apps under `apps/`.
"""

from datetime import timedelta
from pathlib import Path

import environ

from common.db import build_database_config

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    ENVIRONMENT=(str, 'development'),
    DJANGO_DEBUG=(bool, True),
    DJANGO_ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    DB_ENGINE=(str, 'django.db.backends.sqlite3'),
    DB_NAME=(str, 'db.sqlite3'),
    DB_USER=(str, 'root'),
    DB_PASSWORD=(str, ''),
    DB_HOST=(str, '127.0.0.1'),
    DB_PORT=(str, '3306'),
    DB_CONN_MAX_AGE=(int, 60),
    CORS_ALLOWED_ORIGINS=(list, ['http://localhost:5173', 'http://127.0.0.1:5173']),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 60),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    DEFAULT_ATTRIBUTION_MODEL=(str, 'position_based'),
    DEFAULT_CONVERSION_WINDOW_DAYS=(int, 90),
    TIME_DECAY_HALF_LIFE_DAYS=(int, 7),
    DEFAULT_CURRENCY=(str, 'USD'),
)

ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)

ENVIRONMENT = env('ENVIRONMENT')
SECRET_KEY = env(
    'DJANGO_SECRET_KEY',
    default='django-insecure-stage1-dev-only-change-before-production',
)
DEBUG = env('DJANGO_DEBUG')
ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')

# ---------------------------------------------------------------------------
# Application Definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'drf_spectacular',
]

# Domain apps registered across AttributionIQ modules.
LOCAL_APPS = [
    'apps.accounts',
    'apps.channels',
    'apps.campaigns',
    'apps.creatives',
    'apps.audiences',
    'apps.contacts',
    'apps.web_sessions',
    'apps.touchpoints',
    'apps.leads',
    'apps.opportunities',
    'apps.orders',
    'apps.costs',
    'apps.attribution',
    'apps.analytics',
    'apps.exceptions',
    'apps.audit',
    'apps.validation',
    'data_generator',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Database Configuration (Environment-driven MySQL or SQLite fallback)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': build_database_config(
        base_dir=BASE_DIR,
        engine=env('DB_ENGINE'),
        name=env('DB_NAME'),
        user=env('DB_USER'),
        password=env('DB_PASSWORD'),
        host=env('DB_HOST'),
        port=env('DB_PORT'),
        conn_max_age=env('DB_CONN_MAX_AGE'),
    )
}

# ---------------------------------------------------------------------------
# Password Validation & Internationalization
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Django REST Framework, JWT & OpenAPI
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    'COERCE_DECIMAL_TO_STRING': False,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env('JWT_ACCESS_TOKEN_LIFETIME_MINUTES')),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env('JWT_REFRESH_TOKEN_LIFETIME_DAYS')),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

EMAIL_BACKEND = env.str('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env.str('DEFAULT_FROM_EMAIL', default='noreply@attributioniq.io')

SPECTACULAR_SETTINGS = {
    'TITLE': 'AttributionIQ — Marketing Attribution & ROI Intelligence API',
    'DESCRIPTION': (
        'Enterprise backend APIs for campaign management, customer touchpoint tracking, '
        'multi-touch attribution modeling, ROI analytics, data quality validation, '
        'and deterministic synthetic data generation.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'COMPONENT_SPLIT_REQUEST': True,
    'ENUM_NAME_OVERRIDES': {
        'UserAccountStatusEnum': 'apps.accounts.models.UserProfile.AccountStatus',
        'ChannelStatusEnum': 'apps.channels.models.Channel.Status',
        'CampaignStatusEnum': 'apps.campaigns.models.Campaign.Status',
        'CreativeStatusEnum': 'apps.creatives.models.Creative.Status',
        'AudienceStatusEnum': 'apps.audiences.models.Audience.Status',
        'LeadStatusEnum': 'apps.leads.models.Lead.Status',
        'OpportunityStatusEnum': 'apps.opportunities.models.Opportunity.Status',
        'AttributionRunStatusEnum': 'apps.attribution.models.AttributionRun.Status',
        'AttributionModelCodeEnum': 'apps.attribution.models.AttributionModel.ModelCode',
        'ValidationCheckStatusEnum': 'apps.validation.models.ValidationCheckResult.Status',
        'CurrencyEnum': 'apps.campaigns.models.Campaign.Currency',
    },
}

# ---------------------------------------------------------------------------
# CORS Configuration (React + Vite Development Server)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Attribution Engine Defaults
# ---------------------------------------------------------------------------
ATTRIBUTION_SETTINGS = {
    'DEFAULT_MODEL': env('DEFAULT_ATTRIBUTION_MODEL'),
    'CONVERSION_WINDOW_DAYS': env('DEFAULT_CONVERSION_WINDOW_DAYS'),
    'TIME_DECAY_HALF_LIFE_DAYS': env('TIME_DECAY_HALF_LIFE_DAYS'),
    'DEFAULT_CURRENCY': env('DEFAULT_CURRENCY'),
    'SUPPORTED_CURRENCIES': ['USD', 'EUR', 'GBP'],
}

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} ({module}:{lineno}) - {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'backend.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'attribution': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

