from django.apps import AppConfig


class AttributionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.attribution'
    label = 'attribution'
    verbose_name = 'Attribution Engine'

