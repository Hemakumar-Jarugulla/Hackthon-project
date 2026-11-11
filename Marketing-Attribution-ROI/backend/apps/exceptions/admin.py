from django.contrib import admin

from apps.exceptions.models import DataException


@admin.register(DataException)
class DataExceptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'issue_type',
        'entity_type',
        'entity_id',
        'severity',
        'resolution_status',
        'created_date',
    )
    list_filter = ('issue_type', 'entity_type', 'severity', 'resolution_status')
    search_fields = ('id', 'entity_id', 'description')

