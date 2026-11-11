from django.contrib import admin

from apps.campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignCreative,
    CampaignStatusHistory,
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'channel', 'budget', 'currency', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'currency', 'channel')
    search_fields = ('id', 'name', 'objective')


admin.site.register(CampaignCreative)
admin.site.register(CampaignAudience)
admin.site.register(CampaignStatusHistory)

