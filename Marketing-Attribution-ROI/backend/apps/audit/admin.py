from django.contrib import admin

from apps.audit.models import AuditLog, IdSequence


@admin.register(IdSequence)
class IdSequenceAdmin(admin.ModelAdmin):
    list_display = ('scope_key', 'last_value', 'updated_at')
    search_fields = ('scope_key',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'entity_type', 'entity_id', 'action', 'actor', 'created_at')
    list_filter = ('action', 'entity_type')
    search_fields = ('entity_type', 'entity_id', 'notes')

