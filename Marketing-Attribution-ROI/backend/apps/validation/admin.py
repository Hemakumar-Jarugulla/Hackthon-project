from django.contrib import admin

from apps.validation.models import ValidationCheckResult, ValidationRun


@admin.register(ValidationRun)
class ValidationRunAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'triggered_by',
        'total_checks',
        'passed_checks',
        'failed_checks',
        'warning_checks',
        'executed_at',
    )
    search_fields = ('id', 'triggered_by')


@admin.register(ValidationCheckResult)
class ValidationCheckResultAdmin(admin.ModelAdmin):
    list_display = (
        'check_code',
        'check_name',
        'run',
        'category',
        'status',
        'failed_records',
        'records_checked',
    )
    list_filter = ('status', 'category')
    search_fields = ('check_code', 'check_name', 'entity', 'details')

