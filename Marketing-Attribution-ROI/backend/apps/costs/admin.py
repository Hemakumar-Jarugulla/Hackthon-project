from django.contrib import admin

from apps.costs.models import CostRecord


@admin.register(CostRecord)
class CostRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'channel', 'category', 'amount', 'currency', 'spend_date')
    list_filter = ('category', 'currency', 'channel')
    search_fields = ('id', 'campaign__id', 'campaign__name', 'description')

