
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import User
from members.models import Member
from wallets.models import Wallet, WalletTransaction

from .models import Withdrawal
from .forms import (
    WithdrawalRequestForm,
    WithdrawalPaymentForm,
    WithdrawalRejectionForm,
)


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.ACCOUNTANT,
    User.Role.MEMBER,
)
def withdrawal_list(request):

    withdrawals = Withdrawal.objects.select_related(
        'member',
        'requested_by',
        'approved_by',
        'paid_by',
    )

    if request.user.role == User.Role.MEMBER:
        withdrawals = withdrawals.filter(
            member__user=request.user
        )

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if search:
        withdrawals = withdrawals.filter(
            request_no__icontains=search
        ) | withdrawals.filter(
            member__member_no__icontains=search
        )

    if status:
        withdrawals = withdrawals.filter(status=status)

    stats = {
        'total': withdrawals.count(),
        'pending': withdrawals.filter(
            status=Withdrawal.Status.PENDING
        ).count(),
        'approved': withdrawals.filter(
            status=Withdrawal.Status.APPROVED
        ).count(),
        'paid_amount': withdrawals.filter(
            status=Withdrawal.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
    }

    paginator = Paginator(withdrawals.distinct(), 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'withdrawals': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'search': search,
        'selected_status': status,
        'status_choices': Withdrawal.Status.choices,
    }

    return render(
        request,
        'withdrawals/withdrawal_list.html',
        context
    )


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.MEMBER,
)
def withdrawal_create(request):

    if request.user.role == User.Role.MEMBER:
        member = get_object_or_404(
            Member,
            user=request.user,
            status=Member.Status.ACTIVE,
        )
    else:
        member_id = request.GET.get('member')

        if not member_id:
            messages.error(request, 'Select a member first.')
            return redirect('members:member_list')

        member = get_object_or_404(
            Member,
            pk=member_id,
            status=Member.Status.ACTIVE,
        )

    wallet = Wallet.objects.filter(
        member=member,
        is_active=True
    ).first()

    if not wallet:
        messages.error(request, 'This member does not have an active wallet.')
        return redirect('withdrawals:withdrawal_list')

    if request.method == 'POST':
        form = WithdrawalRequestForm(request.POST)

        if form.is_valid():
            amount = form.cleaned_data['amount']

            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

                if amount > wallet.balance:
                    form.add_error(
                        'amount',
                        'Withdrawal amount exceeds the available balance.'
                    )
                else:
                    withdrawal = form.save(commit=False)
                    withdrawal.member = member
                    withdrawal.requested_by = request.user
                    withdrawal.full_clean()
                    withdrawal.save()

                    messages.success(
                        request,
                        'Withdrawal request submitted successfully.'
                    )

                    return redirect(
                        'withdrawals:withdrawal_detail',
                        pk=withdrawal.pk
                    )
    else:
        form = WithdrawalRequestForm()

    return render(
        request,
        'withdrawals/withdrawal_form.html',
        {
            'form': form,
            'member': member,
            'wallet': wallet,
        }
    )


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.ACCOUNTANT,
    User.Role.MEMBER,
)
def withdrawal_detail(request, pk):

    withdrawal = get_object_or_404(
        Withdrawal.objects.select_related(
            'member',
            'requested_by',
            'approved_by',
            'rejected_by',
            'paid_by',
        ),
        pk=pk
    )

    if request.user.role == User.Role.MEMBER:
        if withdrawal.member.user_id != request.user.id:
            messages.error(request, 'You cannot access this withdrawal.')
            return redirect('withdrawals:withdrawal_list')

    return render(
        request,
        'withdrawals/withdrawal_detail.html',
        {'withdrawal': withdrawal}
    )


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def withdrawal_approve(request, pk):

    with transaction.atomic():
        withdrawal = get_object_or_404(
            Withdrawal.objects.select_for_update(),
            pk=pk
        )

        if withdrawal.status != Withdrawal.Status.PENDING:
            messages.error(request, 'This request is no longer pending.')
        else:
            wallet = Wallet.objects.select_for_update().filter(
                member=withdrawal.member,
                is_active=True
            ).first()

            if not wallet or wallet.balance < withdrawal.amount:
                messages.error(
                    request,
                    'Insufficient wallet balance. Request cannot be approved.'
                )
            else:
                withdrawal.status = Withdrawal.Status.APPROVED
                withdrawal.approved_by = request.user
                withdrawal.approved_at = timezone.now()
                withdrawal.save(update_fields=[
                    'status',
                    'approved_by',
                    'approved_at',
                    'updated_at',
                ])
                messages.success(request, 'Withdrawal approved.')

    return redirect('withdrawals:withdrawal_detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def withdrawal_reject(request, pk):

    withdrawal = get_object_or_404(Withdrawal, pk=pk)

    if withdrawal.status != Withdrawal.Status.PENDING:
        messages.error(request, 'Only pending requests can be rejected.')
        return redirect('withdrawals:withdrawal_detail', pk=pk)

    form = WithdrawalRejectionForm(request.POST)

    if form.is_valid():
        with transaction.atomic():
            withdrawal = get_object_or_404(
                Withdrawal.objects.select_for_update(),
                pk=pk
            )

            if withdrawal.status == Withdrawal.Status.PENDING:
                withdrawal.status = Withdrawal.Status.REJECTED
                withdrawal.rejected_by = request.user
                withdrawal.rejected_at = timezone.now()
                withdrawal.rejection_reason = form.cleaned_data[
                    'rejection_reason'
                ]
                withdrawal.save(update_fields=[
                    'status',
                    'rejected_by',
                    'rejected_at',
                    'rejection_reason',
                    'updated_at',
                ])
                messages.success(request, 'Withdrawal rejected.')
            else:
                messages.error(request, 'This request has already been processed.')

    return redirect('withdrawals:withdrawal_detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN, User.Role.ACCOUNTANT)
@require_POST
def withdrawal_pay(request, pk):

    withdrawal = get_object_or_404(
        Withdrawal.objects.select_related('member'),
        pk=pk
    )

    form = WithdrawalPaymentForm(request.POST, instance=withdrawal)

    if not form.is_valid():
        messages.error(request, 'Please correct the payment information.')
        return redirect('withdrawals:withdrawal_detail', pk=pk)

    try:
        with transaction.atomic():
            withdrawal = Withdrawal.objects.select_for_update().get(pk=pk)

            if withdrawal.status != Withdrawal.Status.APPROVED:
                raise ValidationError(
                    'Only approved withdrawals can be paid.'
                )

            wallet = Wallet.objects.select_for_update().get(
                member=withdrawal.member,
                is_active=True
            )

            if wallet.balance < withdrawal.amount:
                raise ValidationError(
                    'Insufficient wallet balance.'
                )

            existing = WalletTransaction.objects.filter(
                withdrawal=withdrawal
            ).exists()

            if existing:
                raise ValidationError(
                    'A wallet transaction already exists for this withdrawal.'
                )

            balance_before = wallet.balance
            balance_after = balance_before - withdrawal.amount

            WalletTransaction.objects.create(
                wallet=wallet,
                withdrawal=withdrawal,
                transaction_type=WalletTransaction.TransactionType.DEBIT,
                amount=withdrawal.amount,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f'Withdrawal payment - {withdrawal.request_no}',
                reference=f'WDR-{withdrawal.pk:08d}',
                created_by=request.user,
            )

            wallet.balance = balance_after
            wallet.save(update_fields=['balance', 'updated_at'])

            withdrawal.payment_method = form.cleaned_data['payment_method']
            withdrawal.payment_reference = form.cleaned_data[
                'payment_reference'
            ]
            withdrawal.notes = form.cleaned_data['notes']
            withdrawal.status = Withdrawal.Status.PAID
            withdrawal.paid_by = request.user
            withdrawal.paid_at = timezone.now()

            withdrawal.save(update_fields=[
                'payment_method',
                'payment_reference',
                'notes',
                'status',
                'paid_by',
                'paid_at',
                'updated_at',
            ])

        messages.success(request, 'Withdrawal payment completed successfully.')

    except (ValidationError, Wallet.DoesNotExist) as exc:
        messages.error(
            request,
            exc.message if hasattr(exc, 'message') else str(exc)
        )

    return redirect('withdrawals:withdrawal_detail', pk=pk)
