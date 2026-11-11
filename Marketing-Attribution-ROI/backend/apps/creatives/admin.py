from django.contrib import admin

from apps.creatives.models import Creative


@admin.register(Creative)
class CreativeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'creative_type', 'primary_campaign', 'status', 'start_date', 'end_date')
    list_filter = ('creative_type', 'status')
    search_fields = ('id', 'name', 'description')

