from django.contrib import admin

from apps.web_sessions.models import WebSession


@admin.register(WebSession)
class WebSessionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'anonymous_id',
        'contact',
        'campaign',
        'identity_status',
        'has_evidence',
        'device_type',
        'timestamp',
    )
    list_filter = ('identity_status', 'has_evidence', 'device_type')
    search_fields = ('id', 'anonymous_id', 'landing_page', 'linking_issue')

