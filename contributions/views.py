from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from .models import ContributionPlan
from .forms import ContributionPlanForm


# LIST CONTRIBUTION PLANS
@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def plan_list(request):

    plans = ContributionPlan.objects.all()

    search = request.GET.get('search', '').strip()
    frequency = request.GET.get('frequency', '')
    status = request.GET.get('status', '')

    if search:
        plans = plans.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )

    if frequency:
        plans = plans.filter(frequency=frequency)

    if status == 'active':
        plans = plans.filter(is_active=True)
    elif status == 'inactive':
        plans = plans.filter(is_active=False)

    paginator = Paginator(plans, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'plans': page_obj.object_list,
        'search': search,
        'selected_frequency': frequency,
        'selected_status': status,
        'frequency_choices': ContributionPlan.Frequency.choices,
        'total_plans': ContributionPlan.objects.count(),
        'active_plans': ContributionPlan.objects.filter(
            is_active=True
        ).count(),
        'inactive_plans': ContributionPlan.objects.filter(
            is_active=False
        ).count(),
    }

    return render(
        request,
        'contributions/plan_list.html',
        context
    )


# CREATE CONTRIBUTION PLAN
@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def plan_create(request):

    if request.method == 'POST':
        form = ContributionPlanForm(request.POST)

        if form.is_valid():
            plan = form.save(commit=False)
            plan.created_by = request.user
            plan.save()

            messages.success(
                request,
                'Contribution plan created successfully.'
            )
            return redirect('contributions:plan_detail', pk=plan.pk)

    else:
        form = ContributionPlanForm()

    return render(
        request,
        'contributions/plan_form.html',
        {
            'form': form,
            'page_title': 'Create Contribution Plan',
        }
    )


# CONTRIBUTION PLAN DETAIL
@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def plan_detail(request, pk):

    plan = get_object_or_404(ContributionPlan, pk=pk)

    return render(
        request,
        'contributions/plan_detail.html',
        {'plan': plan}
    )


# UPDATE CONTRIBUTION PLAN
@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def plan_update(request, pk):

    plan = get_object_or_404(ContributionPlan, pk=pk)

    if request.method == 'POST':
        form = ContributionPlanForm(request.POST, instance=plan)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                'Contribution plan updated successfully.'
            )
            return redirect('contributions:plan_detail', pk=plan.pk)

    else:
        form = ContributionPlanForm(instance=plan)

    return render(
        request,
        'contributions/plan_form.html',
        {
            'form': form,
            'plan': plan,
            'page_title': 'Edit Contribution Plan',
        }
    )


# ACTIVATE / DEACTIVATE PLAN
@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def plan_toggle_status(request, pk):

    plan = get_object_or_404(ContributionPlan, pk=pk)

    plan.is_active = not plan.is_active
    plan.save(update_fields=['is_active', 'updated_at'])

    if plan.is_active:
        messages.success(request, 'Contribution plan activated.')
    else:
        messages.success(request, 'Contribution plan deactivated.')

    return redirect('contributions:plan_detail', pk=plan.pk)