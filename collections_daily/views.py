from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.db.models import Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from .models import Collection
from .forms import CollectionForm

from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CollectionRejectionForm

User = get_user_model()


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.AGENT,
)
def collection_list(request):
    collections = Collection.objects.select_related(
        'enrollment__member',
        'enrollment__plan',
        'assignment__agent__user',
        'collected_by',
    )

    # Agents can only see collections they recorded.
    if request.user.role == User.Role.AGENT:
        collections = collections.filter(collected_by=request.user)

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if search:
        collections = collections.filter(
            Q(receipt_no__icontains=search)
            | Q(enrollment__member__member_no__icontains=search)
            | Q(enrollment__member__first_name__icontains=search)
            | Q(enrollment__member__last_name__icontains=search)
            | Q(transaction_reference__icontains=search)
        )

    if status:
        collections = collections.filter(status=status)

    total_amount = collections.aggregate(
        total=Sum('amount')
    )['total'] or 0

    pending_amount = collections.filter(
        status=Collection.Status.PENDING
    ).aggregate(total=Sum('amount'))['total'] or 0

    verified_amount = collections.filter(
        status=Collection.Status.VERIFIED
    ).aggregate(total=Sum('amount'))['total'] or 0

    paginator = Paginator(collections, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'collections': page_obj.object_list,
        'search': search,
        'selected_status': status,
        'status_choices': Collection.Status.choices,
        'total_amount': total_amount,
        'pending_amount': pending_amount,
        'verified_amount': verified_amount,
    }

    return render(request, 'collections/collection_list.html', context)


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.AGENT,
)
def collection_create(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST, user=request.user)

        if form.is_valid():
            try:
                with transaction.atomic():
                    collection = form.save(commit=False)
                    collection.collected_by = request.user

                    # Recheck the assignment inside the transaction.
                    collection.full_clean()
                    collection.save()

                messages.success(
                    request,
                    f'Collection recorded successfully. '
                    f'Receipt: {collection.receipt_no}'
                )
                return redirect(
                    'collections:collection_detail',
                    pk=collection.pk,
                )

            except IntegrityError:
                messages.error(
                    request,
                    'The collection could not be saved. Please try again.'
                )
    else:
        form = CollectionForm(user=request.user)

    return render(
        request,
        'collections/collection_form.html',
        {'form': form},
    )


@login_required
@role_required(
    User.Role.ADMIN,
    User.Role.MANAGER,
    User.Role.AGENT,
)
def collection_detail(request, pk):
    collection = get_object_or_404(
        Collection.objects.select_related(
            'enrollment__member',
            'enrollment__plan',
            'assignment__agent__user',
            'collected_by',
            'verified_by',
        ),
        pk=pk,
    )

    if (
        request.user.role == User.Role.AGENT
        and collection.collected_by_id != request.user.id
    ):
        messages.error(request, 'You cannot view this collection.')
        return redirect('collections:collection_list')

    return render(
        request,
        'collections/collection_detail.html',
        {'collection': collection},
    )

@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def collection_verify(request, pk):
    with transaction.atomic():
        collection = get_object_or_404(
            Collection.objects.select_for_update(),
            pk=pk,
        )

        if collection.status != Collection.Status.PENDING:
            messages.warning(
                request,
                'This collection has already been processed.'
            )
            return redirect(
                'collections:collection_detail',
                pk=collection.pk,
            )

        collection.status = Collection.Status.VERIFIED
        collection.verified_by = request.user
        collection.verified_at = timezone.now()
        collection.rejection_reason = ''
        collection.rejected_by = None
        collection.rejected_at = None

        collection.save(update_fields=[
            'status',
            'verified_by',
            'verified_at',
            'rejection_reason',
            'rejected_by',
            'rejected_at',
            'updated_at',
        ])

    messages.success(
        request,
        f'Collection {collection.receipt_no} has been verified.'
    )

    return redirect(
        'collections:collection_detail',
        pk=collection.pk,
    )


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def collection_reject(request, pk):
    collection = get_object_or_404(Collection, pk=pk)

    form = CollectionRejectionForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'Please provide a valid rejection reason.')
        return redirect(
            'collections:collection_detail',
            pk=collection.pk,
        )

    with transaction.atomic():
        collection = get_object_or_404(
            Collection.objects.select_for_update(),
            pk=pk,
        )

        if collection.status != Collection.Status.PENDING:
            messages.warning(
                request,
                'This collection has already been processed.'
            )
            return redirect(
                'collections:collection_detail',
                pk=collection.pk,
            )

        collection.status = Collection.Status.REJECTED
        collection.rejection_reason = form.cleaned_data['rejection_reason']
        collection.rejected_by = request.user
        collection.rejected_at = timezone.now()

        collection.save(update_fields=[
            'status',
            'rejection_reason',
            'rejected_by',
            'rejected_at',
            'updated_at',
        ])

    messages.success(
        request,
        f'Collection {collection.receipt_no} has been rejected.'
    )

    return redirect(
        'collections:collection_detail',
        pk=collection.pk,
    )






