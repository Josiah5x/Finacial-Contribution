from django.contrib import admin
from .models import Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'member',
        'balance',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active',)
    search_fields = (
        'member__member_no',
        'member__first_name',
        'member__last_name',
    )
    readonly_fields = ('balance', 'created_at', 'updated_at')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'wallet',
        'transaction_type',
        'amount',
        'balance_before',
        'balance_after',
        'created_at',
    )
    list_filter = ('transaction_type', 'created_at')
    search_fields = (
        'reference',
        'wallet__member__member_no',
        'wallet__member__first_name',
        'wallet__member__last_name',
    )
    readonly_fields = (
        'wallet',
        'collection',
        'transaction_type',
        'amount',
        'balance_before',
        'balance_after',
        'reference',
        'created_by',
        'created_at',
    )