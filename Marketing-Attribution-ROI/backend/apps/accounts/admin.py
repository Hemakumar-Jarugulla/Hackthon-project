from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = 'user'
    readonly_fields = ('user_code', 'last_active_at', 'created_at', 'updated_at')


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_code',
        'user',
        'role',
        'department',
        'timezone',
        'status',
        'last_active_at',
        'created_at',
    )
    list_filter = ('role', 'status', 'timezone')
    search_fields = ('user_code', 'user__username', 'user__email', 'department')
    readonly_fields = ('user_code', 'last_active_at', 'created_at', 'updated_at')
