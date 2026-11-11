from django.contrib import admin

from apps.leads.models import Lead, LeadStatusHistory


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('id', 'contact', 'campaign', 'source', 'score', 'status', 'created_date')
    list_filter = ('status', 'source')
    search_fields = ('id', 'contact__name', 'contact__email', 'source')


admin.site.register(LeadStatusHistory)

