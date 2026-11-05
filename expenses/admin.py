from django.contrib import admin
from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'title',
        'category',
        'amount',
        'expense_date',
        'status',
        'recorded_by',
    )

    list_filter = (
        'status',
        'payment_method',
        'category',
        'expense_date',
    )

    search_fields = (
        'reference',
        'title',
        'paid_to',
    )

    readonly_fields = (
        'reference',
        'created_at',
        'updated_at',
        'approved_at',
        'rejected_at',
        'paid_at',
    )