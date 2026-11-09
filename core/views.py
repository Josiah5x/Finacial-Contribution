

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist

from collections_daily.models import Collection
from withdrawals.models import Withdrawal
from members.models import Member,MemberAssignment
from django.db.models import Sum
from datetime import date, timedelta

from decimal import Decimal


from accounts.models import User
from wallets.models import Wallet
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

    # Members use their own dashboard
    if user.role == User.Role.MEMBER:
        return redirect('member_dashboard')

    today = timezone.localdate()
    zero = Decimal('0.00')

    # ----------------------------------
    # Member statistics
    # ----------------------------------
    total_members = Member.objects.count()

    active_members = Member.objects.filter(
        status=Member.Status.ACTIVE
    ).count()

    pending_members = Member.objects.filter(
        status=Member.Status.PENDING
    ).count()

    # ----------------------------------
    # Agent and user statistics
    # ----------------------------------
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

    # ----------------------------------
    # Verified collections
    # ----------------------------------
    verified_collections = Collection.objects.filter(
        status=Collection.Status.VERIFIED
    )

    today_collection = (
        verified_collections.filter(
            collection_date=today
        ).aggregate(total=Sum('amount'))['total'] or zero
    )

    total_collections = (
        verified_collections.aggregate(
            total=Sum('amount')
        )['total'] or zero
    )

    cash_collections = (
        verified_collections.filter(
            payment_method=Collection.PaymentMethod.CASH
        ).aggregate(total=Sum('amount'))['total'] or zero
    )

    transfer_collections = (
        verified_collections.filter(
            payment_method=Collection.PaymentMethod.BANK_TRANSFER
        ).aggregate(total=Sum('amount'))['total'] or zero
    )

    pending_payments = Collection.objects.filter(
        status=Collection.Status.PENDING
    ).count()

    rejected_collections = Collection.objects.filter(
        status=Collection.Status.REJECTED
    ).count()

    # ----------------------------------
    # Last seven days chart data
    # ----------------------------------
    start_date = today - timedelta(days=6)

    daily_totals = (
        verified_collections.filter(
            collection_date__range=(start_date, today)
        )
        .values('collection_date')
        .annotate(total=Sum('amount'))
    )

    daily_totals_map = {
        item['collection_date']: float(item['total'])
        for item in daily_totals
    }

    collection_chart_labels = []
    collection_chart_values = []

    for day_offset in range(7):
        chart_date = start_date + timedelta(days=day_offset)

        collection_chart_labels.append(
            chart_date.strftime('%a')
        )

        collection_chart_values.append(
            daily_totals_map.get(chart_date, 0)
        )

    # ----------------------------------
    # Withdrawals
    # ----------------------------------
    pending_withdrawals = Withdrawal.objects.filter(
        status=Withdrawal.Status.PENDING
    ).count()

    approved_withdrawals = Withdrawal.objects.filter(
        status=Withdrawal.Status.APPROVED
    ).count()

    paid_withdrawals = (
        Withdrawal.objects.filter(
            status=Withdrawal.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or zero
    )

    # ----------------------------------
    # Wallets
    # ----------------------------------
    wallet_balance = (
        Wallet.objects.filter(
            is_active=True
        ).aggregate(total=Sum('balance'))['total'] or zero
    )

    # ----------------------------------
    # Agent-specific statistics
    # ----------------------------------
    my_members_count = 0
    agent_today_collection = zero
    daily_collection_target = zero

    if user.role == User.Role.AGENT:
        my_members_count = MemberAssignment.objects.filter(
            agent__user=user,
            is_active=True
        ).count()

        agent_today_collection = (
            verified_collections.filter(
                assignment__agent__user=user,
                collection_date=today
            ).aggregate(total=Sum('amount'))['total'] or zero
        )

        agent_profile = getattr(user, 'agent_profile', None)

        if agent_profile:
            daily_collection_target = agent_profile.daily_target

    # ----------------------------------
    # Dashboard context
    # ----------------------------------
    context = {
        'today': today,

        # Members
        'total_members': total_members,
        'active_members': active_members,
        'pending_members': pending_members,

        # Agents and users
        'total_agents': total_agents,
        'active_agents': active_agents,
        'total_managers': total_managers,
        'total_users': total_users,

        # Collections
        'today_collection': today_collection,
        'total_collections': total_collections,
        'member_contributions': total_collections,
        'cash_collections': cash_collections,
        'transfer_collections': transfer_collections,
        'pending_payments': pending_payments,
        'rejected_collections': rejected_collections,

        # Charts
        'collection_chart_labels': collection_chart_labels,
        'collection_chart_values': collection_chart_values,
        'payment_chart_values': [
            float(cash_collections),
            float(transfer_collections),
        ],

        # Withdrawals
        'pending_withdrawals': pending_withdrawals,
        'approved_withdrawals': approved_withdrawals,
        'paid_withdrawals': paid_withdrawals,

        # Wallet
        'wallet_balance': wallet_balance,

        # Agent dashboard
        'my_members_count': my_members_count,
        'agent_today_collection': agent_today_collection,
        'daily_collection_target': daily_collection_target,

        # To be connected after inspecting expenses/models.py
        'total_expenses': zero,
    }

    return render(
        request,
        'dashboard/index.html',
        context
    )