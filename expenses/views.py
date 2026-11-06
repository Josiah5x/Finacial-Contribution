from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from expenses.models import Expense

from accounts.decorators import role_required
from .models import Expense, ExpenseCategory
from .forms import (
    ExpenseCategoryForm,
    ExpenseForm,
    ExpensePaymentForm,
    ExpenseRejectionForm,
)


STAFF_ROLES = ('ADMIN', 'MANAGER', 'ACCOUNTANT')


@login_required
@role_required('ADMIN', 'MANAGER')
def category_list(request):
    categories = ExpenseCategory.objects.all()

    query = request.GET.get('q', '').strip()
    if query:
        categories = categories.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    return render(request, 'expenses/category_list.html', {
        'categories': categories,
        'query': query,
    })


@login_required
@role_required('ADMIN', 'MANAGER')
def category_create(request):
    form = ExpenseCategoryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Expense category created successfully.')
        return redirect('expenses:category_list')

    return render(request, 'expenses/category_form.html', {
        'form': form,
        'title': 'Create Expense Category',
    })


@login_required
@role_required(*STAFF_ROLES)
def expense_list(request):
    expenses = Expense.objects.select_related(
        'category', 'recorded_by', 'approved_by', 'paid_by'
    )

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if query:
        expenses = expenses.filter(
            Q(reference__icontains=query) |
            Q(title__icontains=query) |
            Q(paid_to__icontains=query) |
            Q(category__name__icontains=query)
        )

    if status:
        expenses = expenses.filter(status=status)

    totals = Expense.objects.aggregate(
        total_paid=Sum('amount', filter=Q(status=Expense.Status.PAID)),
        total_pending=Sum('amount', filter=Q(status=Expense.Status.PENDING)),
        total_approved=Sum('amount', filter=Q(status=Expense.Status.APPROVED)),
    )

    total_expenses = (
    Expense.objects.filter(
        status=Expense.Status.PAID
    ).aggregate(total=Sum('amount'))['total'] or 0
    )

    paginator = Paginator(expenses, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'expenses/expense_list.html', {
        'page_obj': page_obj,
        'expenses': page_obj,
        'query': query,
        'selected_status': status,
        'status_choices': Expense.Status.choices,
        'total_paid': totals['total_paid'] or 0,
        'total_pending': totals['total_pending'] or 0,
        'total_approved': totals['total_approved'] or 0,
        'total_expenses': total_expenses,
    })


@login_required
@role_required(*STAFF_ROLES)
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        expense = form.save(commit=False)
        expense.recorded_by = request.user
        expense.status = Expense.Status.PENDING
        expense.save()

        messages.success(
            request,
            f'Expense {expense.reference} submitted for approval.'
        )
        return redirect('expenses:expense_detail', pk=expense.pk)

    return render(request, 'expenses/expense_form.html', {
        'form': form,
        'title': 'Record New Expense',
    })


@login_required
@role_required(*STAFF_ROLES)
def expense_detail(request, pk):
    expense = get_object_or_404(
        Expense.objects.select_related(
            'category',
            'recorded_by',
            'approved_by',
            'rejected_by',
            'paid_by',
        ),
        pk=pk,
    )

    return render(request, 'expenses/expense_detail.html', {
        'expense': expense,
        'payment_form': ExpensePaymentForm(instance=expense),
        'rejection_form': ExpenseRejectionForm(),
    })


@login_required
@role_required('ADMIN', 'MANAGER')
@require_POST
def expense_approve(request, pk):
    with transaction.atomic():
        expense = get_object_or_404(
            Expense.objects.select_for_update(),
            pk=pk,
        )

        if expense.status != Expense.Status.PENDING:
            messages.error(request, 'Only pending expenses can be approved.')
            return redirect('expenses:expense_detail', pk=pk)

        expense.status = Expense.Status.APPROVED
        expense.approved_by = request.user
        expense.approved_at = timezone.now()
        expense.save(update_fields=[
            'status', 'approved_by', 'approved_at', 'updated_at'
        ])

    messages.success(request, 'Expense approved successfully.')
    return redirect('expenses:expense_detail', pk=pk)


@login_required
@role_required('ADMIN', 'MANAGER')
@require_POST
def expense_reject(request, pk):
    form = ExpenseRejectionForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'Please provide a rejection reason.')
        return redirect('expenses:expense_detail', pk=pk)

    with transaction.atomic():
        expense = get_object_or_404(
            Expense.objects.select_for_update(),
            pk=pk,
        )

        if expense.status != Expense.Status.PENDING:
            messages.error(request, 'Only pending expenses can be rejected.')
            return redirect('expenses:expense_detail', pk=pk)

        expense.status = Expense.Status.REJECTED
        expense.rejected_by = request.user
        expense.rejected_at = timezone.now()
        expense.rejection_reason = form.cleaned_data['rejection_reason']
        expense.save(update_fields=[
            'status',
            'rejected_by',
            'rejected_at',
            'rejection_reason',
            'updated_at',
        ])

    messages.success(request, 'Expense rejected.')
    return redirect('expenses:expense_detail', pk=pk)


@login_required
@role_required('ADMIN', 'ACCOUNTANT')
@require_POST
def expense_pay(request, pk):
    with transaction.atomic():
        expense = get_object_or_404(
            Expense.objects.select_for_update(),
            pk=pk,
        )

        if expense.status != Expense.Status.APPROVED:
            messages.error(request, 'Only approved expenses can be marked as paid.')
            return redirect('expenses:expense_detail', pk=pk)

        form = ExpensePaymentForm(request.POST, instance=expense)

        if not form.is_valid():
            messages.error(request, 'Please select a valid payment method.')
            return redirect('expenses:expense_detail', pk=pk)

        expense = form.save(commit=False)
        expense.status = Expense.Status.PAID
        expense.paid_by = request.user
        expense.paid_at = timezone.now()
        expense.save()

    messages.success(request, 'Expense marked as paid successfully.')
    return redirect('expenses:expense_detail', pk=pk)