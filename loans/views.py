from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import role_required
from members.models import Member

from .models import Loan
from .services import calculate_loan_eligibility

from decimal import Decimal

from django.utils import timezone

from members.models import Member

from .forms import LoanApprovalForm, LoanRejectionForm,LoanApplicationForm



@login_required
@role_required('MEMBER')
def loan_apply(request):
    member = get_object_or_404(
        Member,
        user=request.user,
        status='ACTIVE'
    )

    # Prevent multiple pending applications.
    pending_application = Loan.objects.filter(
        member=member,
        status=Loan.Status.PENDING
    ).exists()

    if pending_application:
        messages.warning(
            request,
            'You already have a pending loan application.'
        )
        return redirect('loans:my_loans')

    eligibility = calculate_loan_eligibility(member)

    if request.method == 'POST':
        form = LoanApplicationForm(
            request.POST,
            eligibility=eligibility
        )

        if form.is_valid():
            with transaction.atomic():
                loan = form.save(commit=False)
                loan.member = member
                loan.requested_by = request.user
                loan.save()

            messages.success(
                request,
                'Your loan application has been submitted successfully.'
            )
            return redirect('loans:my_loans')

    else:
        form = LoanApplicationForm(eligibility=eligibility)

    return render(
        request,
        'loans/loan_apply.html',
        {
            'form': form,
            'member': member,
            'eligibility': eligibility,
        }
    )


@login_required
@role_required('MEMBER')
def my_loans(request):
    member = get_object_or_404(
        Member,
        user=request.user
    )

    loans = Loan.objects.filter(
        member=member
    ).order_by('-created_at')

    return render(
        request,
        'loans/my_loans.html',
        {
            'loans': loans,
            'member': member,
        }
    )




@login_required
@role_required('ADMIN', 'MANAGER', 'ACCOUNTANT')
def loan_list(request):
    loans = Loan.objects.select_related(
        'member',
        'requested_by',
        'approved_by',
        'disbursed_by',
    ).order_by('-created_at')

    status = request.GET.get('status')

    if status:
        valid_statuses = [choice[0] for choice in Loan.Status.choices]
        if status in valid_statuses:
            loans = loans.filter(status=status)

    return render(request, 'loans/loan_list.html', {
        'loans': loans,
        'status_choices': Loan.Status.choices,
        'selected_status': status,
    })


@login_required
@role_required('ADMIN', 'MANAGER', 'ACCOUNTANT')
def loan_detail(request, pk):
    loan = get_object_or_404(
        Loan.objects.select_related(
            'member',
            'requested_by',
            'approved_by',
            'rejected_by',
            'disbursed_by',
        ).prefetch_related('repayments'),
        pk=pk
    )

    eligibility = calculate_loan_eligibility(loan.member)

    return render(request, 'loans/loan_detail.html', {
        'loan': loan,
        'eligibility': eligibility,
    })


@login_required
@role_required('ADMIN', 'MANAGER')
def loan_approve(request, pk):
    if request.method != 'POST':
        return redirect('loans:loan_detail', pk=pk)

    with transaction.atomic():
        loan = get_object_or_404(
            Loan.objects.select_for_update(),
            pk=pk
        )

        if loan.status != Loan.Status.PENDING:
            messages.error(request, 'This loan is no longer pending.')
            return redirect('loans:loan_detail', pk=pk)

        eligibility = calculate_loan_eligibility(loan.member)

        form = LoanApprovalForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'Please correct the approval details.')
            return redirect('loans:loan_detail', pk=pk)

        approved_amount = form.cleaned_data['approved_amount']

        if approved_amount > eligibility['eligible_amount']:
            messages.error(
                request,
                'The approved amount exceeds the member’s current loan eligibility.'
            )
            return redirect('loans:loan_detail', pk=pk)

        loan.verified_contributions = eligibility['verified_contributions']
        loan.eligibility_percentage = eligibility['eligibility_percentage']
        loan.eligible_amount = eligibility['eligible_amount']
        loan.approved_amount = approved_amount
        loan.repayment_months = form.cleaned_data['repayment_months']
        loan.interest_rate = form.cleaned_data['interest_rate']
        loan.status = Loan.Status.APPROVED
        loan.approved_by = request.user
        loan.approved_at = timezone.now()

        loan.save()

    messages.success(request, 'Loan application approved successfully.')
    return redirect('loans:loan_detail', pk=pk)


@login_required
@role_required('ADMIN', 'MANAGER')
def loan_reject(request, pk):
    if request.method != 'POST':
        return redirect('loans:loan_detail', pk=pk)

    form = LoanRejectionForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'Please provide a rejection reason.')
        return redirect('loans:loan_detail', pk=pk)

    with transaction.atomic():
        loan = get_object_or_404(
            Loan.objects.select_for_update(),
            pk=pk
        )

        if loan.status != Loan.Status.PENDING:
            messages.error(request, 'Only pending applications can be rejected.')
            return redirect('loans:loan_detail', pk=pk)

        loan.status = Loan.Status.REJECTED
        loan.rejected_by = request.user
        loan.rejection_reason = form.cleaned_data['rejection_reason']
        loan.save(update_fields=[
            'status',
            'rejected_by',
            'rejection_reason',
            'updated_at',
        ])

    messages.success(request, 'Loan application rejected.')
    return redirect('loans:loan_detail', pk=pk)