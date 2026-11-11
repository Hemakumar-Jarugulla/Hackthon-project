from django.contrib import admin

from apps.audiences.models import Audience


@admin.register(Audience)
class AudienceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'audience_type', 'estimated_size', 'status', 'effective_from', 'effective_to')
    list_filter = ('audience_type', 'status')
    search_fields = ('id', 'name', 'criteria')

