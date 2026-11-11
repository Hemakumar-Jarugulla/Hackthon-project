from django.contrib import admin

from apps.opportunities.models import Opportunity, OpportunityStageHistory


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'contact',
        'lead',
        'stage',
        'status',
        'expected_revenue',
        'actual_revenue',
        'closing_date',
    )
    list_filter = ('stage', 'status')
    search_fields = ('id', 'name', 'contact__name')


admin.site.register(OpportunityStageHistory)

