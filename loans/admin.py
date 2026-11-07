from django.contrib import admin
from .models import Loan, LoanRepayment


class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'loan_no',
        'member',
        'requested_amount',
        'approved_amount',
        'status',
        'created_at',
    )

    list_filter = ('status', 'created_at')
    search_fields = (
        'loan_no',
        'member__member_no',
        'member__user__username',
    )

    readonly_fields = (
        'loan_no',
        'verified_contributions',
        'eligibility_percentage',
        'eligible_amount',
        'created_at',
        'updated_at',
    )

    inlines = [LoanRepaymentInline]


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = (
        'loan',
        'amount',
        'payment_method',
        'repayment_date',
        'received_by',
    )

    list_filter = ('payment_method', 'repayment_date')
    search_fields = ('loan__loan_no', 'reference')