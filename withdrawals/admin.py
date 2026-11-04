
from django.contrib import admin
from .models import Withdrawal


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        'request_no',
        'member',
        'amount',
        'status',
        'payment_method',
        'requested_by',
        'created_at',
    )

    list_filter = (
        'status',
        'payment_method',
        'created_at',
    )

    search_fields = (
        'request_no',
        'member__member_no',
        'member__first_name',
        'member__last_name',
    )

    readonly_fields = (
        'request_no',
        'created_at',
        'updated_at',
        'approved_at',
        'rejected_at',
        'paid_at',
    )
