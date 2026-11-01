from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username',
        'email',
        'phone',
        'role',
        'is_active',
        'is_staff',
    )

    list_filter = ('role', 'is_active', 'is_staff')

    search_fields = (
        'username',
        'email',
        'phone',
    )

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('phone', 'role')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': ('email', 'phone', 'role')
        }),
    )