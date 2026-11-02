from django.contrib import admin
from .models import Collection


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):

    list_display = (
        'receipt_no',
        'enrollment',
        'assignment',
        'amount',
        'payment_method',
        'collection_date',
        'collected_by',
        'status',
    )

    list_filter = (
        'status',
        'payment_method',
        'collection_date',
    )

    search_fields = (
        'receipt_no',
        'enrollment__member__member_no',
        'enrollment__member__first_name',
        'enrollment__member__last_name',
        'transaction_reference',
    )

    readonly_fields = (
        'receipt_no',
        'created_at',
        'updated_at',
        'verified_at',
    )

    date_hierarchy = 'collection_date'