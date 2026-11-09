from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required
from django.views.decorators.http import require_POST

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .forms import AgentForm, AgentUpdateForm
from .models import Agent
from members.models import MemberAssignment
from django.shortcuts import render, redirect, get_object_or_404


User = get_user_model()


@login_required
@role_required(User.Role.ADMIN)
def agent_create(request):

    if request.method == 'POST':
        form = AgentForm(request.POST)

        if form.is_valid():
            with transaction.atomic():

                # Create the agent's login account
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    password=form.cleaned_data['password1'],
                    role=User.Role.AGENT,
                    is_active=True
                )

                # Create the agent profile
                agent = form.save(commit=False)
                agent.user = user
                agent.status = Agent.Status.ACTIVE
                agent.save()

            messages.success(
                request,
                f'{agent.full_name} has been registered as an agent.'
            )

            return redirect('agents:agent_list')

    else:
        form = AgentForm()

    return render(request, 'agents/agent_form.html', {
        'form': form,
        'page_title': 'Register New Agent'
    })




@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def agent_list(request):

    agents = Agent.objects.select_related('user').all()

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if search:
        agents = agents.filter(
            Q(agent_no__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(phone__icontains=search) |
            Q(collection_area__icontains=search)
        )

    if status in dict(Agent.Status.choices):
        agents = agents.filter(status=status)

    total_agents = Agent.objects.count()
    active_agents = Agent.objects.filter(
        status=Agent.Status.ACTIVE
    ).count()
    inactive_agents = Agent.objects.filter(
        status=Agent.Status.INACTIVE
    ).count()

    paginator = Paginator(agents, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search': search,
        'selected_status': status,
        'status_choices': Agent.Status.choices,
        'total_agents': total_agents,
        'active_agents': active_agents,
        'inactive_agents': inactive_agents,
    }

    return render(request, 'agents/agent_list.html', context)



@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.SUPERVISOR
)
def agent_detail(request, pk):

    agent = get_object_or_404(
        Agent.objects.select_related('user'),
        pk=pk
    )

    assignments = agent.member_assignments.filter(
        is_active=True
    ).select_related('member').order_by('-assigned_at')

    context = {
        'agent': agent,
        'assignments': assignments,
        'assigned_members_count': assignments.count(),
    }

    return render(
        request,
        'agents/agent_detail.html',
        context
    )


@login_required
@role_required(User.Role.ADMIN)
def agent_update(request, pk):

    agent = get_object_or_404(
        Agent.objects.select_related('user'),
        pk=pk
    )

    if request.method == 'POST':
        form = AgentUpdateForm(
            request.POST,
            instance=agent
        )

        if form.is_valid():
            with transaction.atomic():
                agent.user.first_name = form.cleaned_data['first_name']
                agent.user.last_name = form.cleaned_data['last_name']
                agent.user.email = form.cleaned_data['email']

                agent.user.save(update_fields=[
                    'first_name',
                    'last_name',
                    'email',
                ])

                form.save()

            messages.success(
                request,
                f'{agent.full_name} updated successfully.'
            )

            return redirect('agents:agent_detail', pk=agent.pk)

    else:
        form = AgentUpdateForm(instance=agent)

    return render(request, 'agents/agent_edit.html', {
        'form': form,
        'agent': agent,
        'page_title': 'Edit Agent'
    })



@login_required
@role_required(User.Role.ADMIN)
@require_POST
def agent_deactivate(request, pk):

    with transaction.atomic():
        agent = get_object_or_404(
            Agent.objects.select_for_update().select_related('user'),
            pk=pk
        )

        if agent.status == Agent.Status.INACTIVE:
            messages.warning(request, 'This agent is already inactive.')
        else:
            agent.status = Agent.Status.INACTIVE
            agent.save(update_fields=['status'])

            agent.user.is_active = False
            agent.user.save(update_fields=['is_active'])

            messages.success(
                request,
                f'{agent.full_name} has been deactivated.'
            )

    return redirect('agents:agent_detail', pk=pk)




@login_required
@role_required(User.Role.ADMIN)
@require_POST
def agent_activate(request, pk):

    with transaction.atomic():
        agent = get_object_or_404(
            Agent.objects.select_for_update().select_related('user'),
            pk=pk
        )

        if agent.status == Agent.Status.ACTIVE:
            messages.warning(request, 'This agent is already active.')
        else:
            agent.status = Agent.Status.ACTIVE
            agent.save(update_fields=['status'])

            agent.user.is_active = True
            agent.user.save(update_fields=['is_active'])

            messages.success(
                request,
                f'{agent.full_name} has been reactivated.'
            )

    return redirect('agents:agent_detail', pk=pk)



@login_required
@role_required('AGENT')
def my_members(request):

    agent = Agent.objects.filter(user=request.user).first()

    if not agent:
        messages.error(
            request,
            "Your Agent profile is not linked to your login account. Contact the administrator."
        )
        return redirect('dashboard')

    assignments = MemberAssignment.objects.filter(
        agent=agent,
        is_active=True
    ).select_related('member')

    return render(request, 'agents/my_members.html', {
        'agent': agent,
        'assignments': assignments,
    })