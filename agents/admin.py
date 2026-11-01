from django.contrib import admin
from .models import Agent


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = (
        'agent_no',
        'full_name',
        'phone',
        'collection_area',
        'daily_target',
        'status',
    )

    list_filter = ('status', 'collection_area')

    search_fields = (
        'agent_no',
        'user__username',
        'user__first_name',
        'user__last_name',
        'phone',
    )

    readonly_fields = (
        'agent_no',
        'created_at',
        'updated_at',
    )

    list_per_page = 25