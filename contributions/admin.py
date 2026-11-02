from django.contrib import admin
from .models import ContributionPlan

from .models import ContributionPlan, PlanEnrollment

@admin.register(ContributionPlan)
class ContributionPlanAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'code',
        'frequency',
        'amount',
        'duration_days',
        'is_active',
        'created_at',
    )

    list_filter = (
        'frequency',
        'is_active',
        'created_at',
    )

    search_fields = (
        'name',
        'code',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )





@admin.register(PlanEnrollment)
class PlanEnrollmentAdmin(admin.ModelAdmin):

    list_display = (
        'member',
        'plan',
        'agreed_amount',
        'start_date',
        'end_date',
        'status',
        'enrolled_by',
    )

    list_filter = (
        'status',
        'plan',
        'start_date',
    )

    search_fields = (
        'member__member_no',
        'member__first_name',
        'member__last_name',
        'plan__name',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )