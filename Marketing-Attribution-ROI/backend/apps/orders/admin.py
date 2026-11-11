from django.contrib import admin

from apps.orders.models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'opportunity',
        'contact',
        'order_date',
        'revenue',
        'currency',
        'payment_status',
        'verification_status',
    )
    list_filter = ('currency', 'payment_status', 'verification_status')
    search_fields = ('id', 'contact__name', 'opportunity__id', 'notes')

