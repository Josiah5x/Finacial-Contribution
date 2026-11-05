from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from accounts.decorators import role_required

from django.shortcuts import render, redirect

from members.models import Member
from .models import Wallet, WalletTransaction

User = get_user_model()




@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.ACCOUNTANT,
    User.Role.MEMBER,
)
def wallet_list(request):

    wallets = Wallet.objects.select_related('member').all()

    # Members can only see their own wallet.
    if request.user.role == User.Role.MEMBER:
        wallets = wallets.filter(member__user=request.user)

    search = request.GET.get('q', '').strip()

    if search and request.user.role != User.Role.MEMBER:
        wallets = wallets.filter(
            Q(member__member_no__icontains=search)
            | Q(member__first_name__icontains=search)
            | Q(member__last_name__icontains=search)
            | Q(member__phone__icontains=search)
        )

    paginator = Paginator(wallets, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'wallets': page_obj.object_list,
        'page_obj': page_obj,
        'search': search,
    }

    return render(request, 'wallets/wallet_list.html', context)


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.ACCOUNTANT,
    User.Role.MEMBER,
)
def wallet_detail(request, pk):

    wallet = get_object_or_404(
        Wallet.objects.select_related('member'),
        pk=pk,
    )

    # Prevent members from accessing another member's wallet.
    if (
        request.user.role == User.Role.MEMBER
        and wallet.member.user_id != request.user.id
    ):
        from django.contrib import messages
        from django.shortcuts import redirect

        messages.error(request, 'You cannot access this wallet.')
        return redirect('wallets:wallet_list')

    transactions = wallet.transactions.select_related(
        'created_by',
        'collection',
    ).all()

    paginator = Paginator(transactions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'wallet': wallet,
        'transactions': page_obj.object_list,
        'page_obj': page_obj,
    }

    return render(request, 'wallets/wallet_detail.html', context)

# ////////////////////////////
@login_required
def member_transactions(request):
    if request.user.role != 'MEMBER':
        return redirect('dashboard')

    member = Member.objects.filter(user=request.user).first()

    if not member:
        return redirect('dashboard')

    wallet = Wallet.objects.filter(member=member).first()

    if not wallet:
        transactions = WalletTransaction.objects.none()
    else:
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')

    transaction_type = request.GET.get('type', '')

    if transaction_type in ['CREDIT', 'DEBIT']:
        transactions = transactions.filter(
            transaction_type=transaction_type
        )

    paginator = Paginator(transactions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'member': member,
        'wallet': wallet,
        'transactions': page_obj,
        'page_obj': page_obj,
        'transaction_type': transaction_type,
    }

    return render(
        request,
        'wallets/member_transactions.html',
        context
    )