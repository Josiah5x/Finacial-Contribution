from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .models import EmailOTP


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




@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'attempts',
        'is_used',
        'expires_at',
        'created_at',
    )

    list_filter = ('is_used', 'created_at')
    search_fields = ('email',)
    readonly_fields = (
        'email',
        'otp_hash',
        'attempts',
        'expires_at',
        'verified_at',
        'created_at',
    )