from django.contrib import admin

from apps.touchpoints.models import Touchpoint


@admin.register(Touchpoint)
class TouchpointAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'contact',
        'campaign',
        'channel',
        'interaction_type',
        'is_online',
        'is_post_conversion',
        'is_valid',
        'timestamp',
    )
    list_filter = ('is_online', 'is_post_conversion', 'is_valid', 'device', 'channel')
    search_fields = ('id', 'interaction_type', 'source', 'validation_notes')

