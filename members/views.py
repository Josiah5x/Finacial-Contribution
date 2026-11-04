from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404


from django.views.decorators.http import require_POST


from accounts.decorators import role_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction

from accounts.models import User
from .forms import MemberForm,MemberAssignment
from .models import Member

from django.contrib.auth import get_user_model
from .forms import MemberCreateForm





@login_required
@role_required(User.Role.ADMIN)
def member_create(request):

    if request.method == 'POST':
        form = MemberCreateForm(request.POST, request.FILES)

        if form.is_valid():
            UserModel = get_user_model()

            with transaction.atomic():

                member = form.save(commit=False)

                # Create login account
                user = UserModel.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
                first_name=member.first_name,
                last_name=member.last_name,
                phone=member.phone,
                role=UserModel.Role.MEMBER,
                is_active=True,
                must_change_password=True,
                )

                # Link account to member profile
                member.user = user
                member.status = Member.Status.ACTIVE
                member.created_by = request.user
                member.save()

            messages.success(
                request,
                f'Member {member.full_name} created successfully. '
                f'Username: {user.username}'
            )

            return redirect(
                'members:member_detail',
                pk=member.pk
            )

    else:
        form = MemberCreateForm()

    return render(
        request,
        'members/member_form.html',
        {
            'form': form,
            'title': 'Register New Member',
            'is_create': True,
        }
    )



@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.SUPERVISOR)
def member_list(request):

    members = Member.objects.all().order_by('-created_at')

    # Search
    search = request.GET.get('q', '').strip()

    if search:
        members = members.filter(
            Q(member_no__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(other_names__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )

    # Filter by status
    status = request.GET.get('status', '')

    if status:
        members = members.filter(status=status)

    # Statistics
    total_members = Member.objects.count()
    active_members = Member.objects.filter(
        status=Member.Status.ACTIVE
    ).count()
    pending_members = Member.objects.filter(
        status=Member.Status.PENDING
    ).count()
    suspended_members = Member.objects.filter(
        status=Member.Status.SUSPENDED
    ).count()

    # Pagination
    paginator = Paginator(members, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'selected_status': status,
        'status_choices': Member.Status.choices,
        'total_members': total_members,
        'active_members': active_members,
        'pending_members': pending_members,
        'suspended_members': suspended_members,
    }

    return render(request, 'members/member_list.html', context)



@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.SUPERVISOR
)



@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        form = MemberForm(
            request.POST,
            request.FILES,
            instance=member
        )

        if form.is_valid():
            with transaction.atomic():
                form.save()

            messages.success(
                request,
                f'{member.full_name} updated successfully.'
            )

            return redirect('members:member_detail', pk=member.pk)

    else:
        form = MemberForm(instance=member)

    return render(request, 'members/member_form.html', {
        'form': form,
        'member': member,
        'page_title': 'Edit Member'
    })


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def member_approve(request, pk):
    with transaction.atomic():
        member = get_object_or_404(
            Member.objects.select_for_update(),
            pk=pk
        )

        if member.status != Member.Status.PENDING:
            messages.warning(request, 'This member is not pending approval.')
            return redirect('members:member_detail', pk=pk)

        member.status = Member.Status.ACTIVE
        member.save(update_fields=['status'])

        if member.user:
            member.user.is_active = True
            member.user.save(update_fields=['is_active'])

    messages.success(request, f'{member.full_name} has been approved.')

    return redirect('members:member_detail', pk=pk)


@login_required
@role_required(User.Role.ADMIN)
@require_POST
def member_suspend(request, pk):
    with transaction.atomic():
        member = get_object_or_404(
            Member.objects.select_for_update(),
            pk=pk
        )

        if member.status != Member.Status.ACTIVE:
            messages.warning(request, 'Only active members can be suspended.')
            return redirect('members:member_detail', pk=pk)

        member.status = Member.Status.SUSPENDED
        member.save(update_fields=['status'])

        if member.user:
            member.user.is_active = False
            member.user.save(update_fields=['is_active'])

    messages.success(request, f'{member.full_name} has been suspended.')

    return redirect('members:member_detail', pk=pk)




@login_required
@role_required(User.Role.ADMIN)
@require_POST
def member_reactivate(request, pk):
    with transaction.atomic():
        member = get_object_or_404(
            Member.objects.select_for_update(),
            pk=pk
        )

        if member.status not in [
            Member.Status.SUSPENDED,
            Member.Status.INACTIVE
        ]:
            messages.warning(request, 'This member cannot be reactivated.')
            return redirect('members:member_detail', pk=pk)

        member.status = Member.Status.ACTIVE
        member.save(update_fields=['status'])

        if member.user:
            member.user.is_active = True
            member.user.save(update_fields=['is_active'])

    messages.success(request, f'{member.full_name} has been reactivated.')

    return redirect('members:member_detail', pk=pk)


def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)

    return render(
        request,
        'members/member_detail.html',
        {'member': member}
    )



@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def assignment_create(request):

    if request.method == 'POST':
        form = MemberAssignmentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    member = Member.objects.select_for_update().get(
                        pk=form.cleaned_data['member'].pk
                    )

                    if MemberAssignment.objects.filter(
                        member=member,
                        is_active=True
                    ).exists():
                        messages.error(
                            request,
                            'This member already has an assigned agent.'
                        )
                        return redirect('members:assignment_create')

                    assignment = form.save(commit=False)
                    assignment.member = member
                    assignment.assigned_by = request.user
                    assignment.save()

                messages.success(
                    request,
                    f'{member.full_name} has been assigned successfully.'
                )

                return redirect(
                    'agents:agent_detail',
                    pk=assignment.agent.pk
                )

            except IntegrityError:
                messages.error(
                    request,
                    'This member already has an active assignment.'
                )

    else:
        form = MemberAssignmentForm()

    return render(request, 'members/assignment_form.html', {
        'form': form,
        'page_title': 'Assign Member to Agent'
    })


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def assignment_transfer(request, pk):

    assignment = get_object_or_404(
        MemberAssignment.objects.select_related(
            'member',
            'agent__user'
        ),
        pk=pk,
        is_active=True
    )

    if request.method == 'POST':
        form = MemberTransferForm(
            request.POST,
            instance=assignment
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    current = MemberAssignment.objects.select_for_update().get(
                        pk=assignment.pk,
                        is_active=True
                    )

                    new_agent = form.cleaned_data['agent']

                    current.end_assignment()

                    new_assignment = MemberAssignment.objects.create(
                        member=current.member,
                        agent=new_agent,
                        assigned_by=request.user,
                        notes=form.cleaned_data['notes']
                    )

                messages.success(
                    request,
                    f'{assignment.member.full_name} transferred successfully.'
                )

                return redirect(
                    'agents:agent_detail',
                    pk=new_assignment.agent.pk
                )

            except IntegrityError:
                messages.error(
                    request,
                    'The transfer could not be completed. Please try again.'
                )

    else:
        form = MemberTransferForm(instance=assignment)

    return render(request, 'members/assignment_transfer.html', {
        'form': form,
        'assignment': assignment,
        'page_title': 'Transfer Member'
    })



@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.SUPERVISOR
)
def assignment_history(request, pk):

    member = get_object_or_404(Member, pk=pk)

    assignments = MemberAssignment.objects.filter(
        member=member
    ).select_related(
        'agent__user',
        'assigned_by'
    ).order_by('-assigned_at')

    return render(request, 'members/assignment_history.html', {
        'member': member,
        'assignments': assignments,
    })








