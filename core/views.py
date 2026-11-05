

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist

from collections_daily.models import Collection
from withdrawals.models import Withdrawal
from members.models import Member
from django.db.models import Sum

User = get_user_model()




@login_required
def member_dashboard(request):
    # Only members can access this dashboard.
    
    
    if request.user.role != 'MEMBER':
        return redirect('dashboard')

    member = Member.objects.filter(user=request.user).first()

    if not member:
        return render(request, 'dashboard/member_dashboard.html', {
            'member': None,
            'wallet': None,
            'enrollments': [],
            'recent_collections': [],
            'recent_withdrawals': [],
            'total_contributions': 0,
        })

    # Get member wallet safely.
    try:
        wallet = member.wallet
    except ObjectDoesNotExist:
        wallet = None

    enrollments = member.plan_enrollments.filter(
        status='ACTIVE'
    ).select_related('plan')

    recent_collections = Collection.objects.filter(
        enrollment__member=member
    ).select_related(
        'enrollment__plan'
    ).order_by('-created_at')[:5]

    recent_withdrawals = Withdrawal.objects.filter(
        member=member
    ).order_by('-created_at')[:5]

    total_contributions = Collection.objects.filter(
    enrollment__member=member,
    status='VERIFIED'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'member': member,
        'wallet': wallet,
        'enrollments': enrollments,
        'recent_collections': recent_collections,
        'recent_withdrawals': recent_withdrawals,
        'total_contributions': total_contributions,
    }

    return render(request, 'dashboard/member_dashboard.html', context)



def landing_page(request):
    if request.user.is_authenticated:
        return render(request, 'dashboard/index.html')

    return render(request, 'core/landing.html')




@login_required
def dashboard(request):

    user = request.user

    # Redirect members to their own dashboard.
    if user.role == User.Role.MEMBER:
        return redirect('member_dashboard')

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

    context = {
        'today': today,
        'total_members': total_members,
        'active_members': active_members,
        'pending_members': pending_members,
        'total_agents': total_agents,
        'active_agents': active_agents,
        'total_managers': total_managers,
        'total_users': total_users,

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

    return render(
        request,
        'dashboard/index.html',
        context
    )