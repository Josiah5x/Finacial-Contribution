

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from members.models import Member

User = get_user_model()



def landing_page(request):
    if request.user.is_authenticated:
        return render(request, 'dashboard/index.html')

    return render(request, 'core/landing.html')




@login_required
def dashboard(request):

    user = request.user
    today = timezone.localdate()

    # General statistics
    total_members = Member.objects.count()

    pending_members = Member.objects.filter(
        status=Member.Status.PENDING
    ).count()

    active_members = Member.objects.filter(
        status=Member.Status.ACTIVE
    ).count()

    total_agents = User.objects.filter(
        role=User.Role.AGENT
    ).count()

    active_agents = User.objects.filter(
        role=User.Role.AGENT,
        is_active=True
    ).count()

    total_managers = User.objects.filter(
        role=User.Role.MANAGER
    ).count()

    total_users = User.objects.count()

    # Default dashboard values
    context = {
        'today': today,

        'total_members': total_members,
        'active_members': active_members,
        'pending_members': pending_members,

        'total_agents': total_agents,
        'active_agents': active_agents,

        'total_managers': total_managers,
        'total_users': total_users,

        # These will be connected when the financial
        # models are completed.
        'today_collection': 0,
        'pending_withdrawals': 0,
        'total_collections': 0,
        'total_expenses': 0,
        'cash_collections': 0,
        'transfer_collections': 0,
        'wallet_balance': 0,
        'member_contributions': 0,
        'pending_payments': 0,
    }

    # Member-specific information
    if user.role == User.Role.MEMBER:
        member = Member.objects.filter(user=user).first()
        context['member'] = member

    return render(
        request,
        'dashboard/index.html',
        context
    )
