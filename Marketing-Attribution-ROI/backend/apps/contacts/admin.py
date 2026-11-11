from django.contrib import admin

from apps.contacts.models import Contact, ContactLifecycleHistory


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'company', 'lifecycle_status', 'created_date')
    list_filter = ('lifecycle_status', 'source')
    search_fields = ('id', 'name', 'email', 'company')


admin.site.register(ContactLifecycleHistory)

