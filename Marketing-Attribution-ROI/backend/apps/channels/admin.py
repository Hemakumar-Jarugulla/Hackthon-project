from django.contrib import admin

from apps.channels.models import Channel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'channel_type', 'status', 'owner')
    list_filter = ('channel_type', 'status')
    search_fields = ('id', 'name', 'owner')

