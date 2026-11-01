
from django.contrib import admin
from .models import Member

from .models import Member, MemberAssignment




@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):

    list_display = (
        'member_no',
        'full_name',
        'phone',
        'gender',
        'status',
        'joined_at',
    )

    list_filter = (
        'status',
        'gender',
        'joined_at',
    )

    search_fields = (
        'member_no',
        'first_name',
        'last_name',
        'phone',
        'email',
    )

    readonly_fields = (
        'member_no',
        'joined_at',
        'created_at',
        'updated_at',
    )

    list_per_page = 25

    actions = ['approve_members']

    @admin.action(description='Approve selected member registrations')
    def approve_members(self, request, queryset):

        approved = 0

        for member in queryset.select_related('user'):

            if member.status != Member.Status.PENDING:
                continue

            member.status = Member.Status.ACTIVE
            member.save(update_fields=['status'])

            if member.user:
                member.user.is_active = True
                member.user.save(update_fields=['is_active'])

            approved += 1

        self.message_user(
            request,
            f'{approved} member account(s) approved successfully.'
        )




@admin.register(MemberAssignment)
class MemberAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        'member',
        'agent',
        'assigned_by',
        'assigned_at',
        'ended_at',
        'is_active',
    )

    list_filter = (
        'is_active',
        'assigned_at',
        'agent',
    )

    search_fields = (
        'member__member_no',
        'member__first_name',
        'member__last_name',
        'agent__agent_no',
        'agent__user__username',
    )

    readonly_fields = (
        'assigned_at',
        'ended_at',
    )



