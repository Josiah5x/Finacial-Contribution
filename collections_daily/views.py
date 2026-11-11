
import uuid

from django.conf import settings
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from members.models import Member, MemberAssignment
from contributions.models import PlanEnrollment
from .models import Collection
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from .forms import CollectionForm

from django.views.decorators.http import require_POST

from .forms import CollectionRejectionForm
from wallets.services import credit_collection

from .paystack import (
    initialize_transaction,
    verify_and_credit_collection,
    PaystackError,
)

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
@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def collection_verify(request, pk):

    try:
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

            collection.save(update_fields=[
                'status',
                'verified_by',
                'verified_at',
                'updated_at',
            ])

            # Automatically credit the member wallet.
            wallet_transaction = credit_collection(
                collection,
                user=request.user,
            )

        messages.success(
            request,
            f'Payment verified successfully. '
            f'₦{wallet_transaction.amount:,.2f} '
            f'credited to the member wallet.'
        )

    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))

    return redirect(
        'collections:collection_detail',
        pk=pk,
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



@login_required
@role_required(User.Role.MEMBER)
def paystack_start(request):

    member = get_object_or_404(
        Member,
        user=request.user,
        status=Member.Status.ACTIVE,
    )

    enrollments = PlanEnrollment.objects.filter(
        member=member,
        status=PlanEnrollment.Status.ACTIVE,
    ).select_related('plan')

    assignment = MemberAssignment.objects.filter(
        member=member,
        is_active=True,
    ).first()

    if not assignment:
        messages.error(
            request,
            'You must be assigned to an agent before making a payment.'
        )
        return redirect('member_dashboard')

    if request.method == 'POST':

        enrollment_id = request.POST.get('enrollment')
        amount = request.POST.get('amount')

        enrollment = get_object_or_404(
            enrollments,
            pk=enrollment_id,
        )

        reference = f'DC-{uuid.uuid4().hex[:24]}'

        collection = Collection(
            enrollment=enrollment,
            assignment=assignment,
            amount=amount,
            payment_method=Collection.PaymentMethod.PAYSTACK,
            transaction_reference=reference,
            paystack_reference=reference,
            collection_date=timezone.localdate(),
            collected_by=request.user,
            status=Collection.Status.PENDING,
        )

        try:
            collection.full_clean()
            collection.save()

            callback_url = request.build_absolute_uri(
                reverse('collections:paystack_callback')
            )

            payment = initialize_transaction(
                email=request.user.email,
                amount=collection.amount,
                reference=reference,
                callback_url=callback_url,
                metadata={
                    'collection_id': collection.pk,
                    'receipt_no': collection.receipt_no,
                },
            )

            collection.paystack_access_code = payment['access_code']
            collection.paystack_authorization_url = (
                payment['authorization_url']
            )

            collection.save(update_fields=[
                'paystack_access_code',
                'paystack_authorization_url',
                'updated_at',
            ])

            return redirect(payment['authorization_url'])

        except Exception as exc:

            messages.error(
                request,
                f'Unable to initialize payment: {exc}'
            )

    return render(
        request,
        'collections/paystack_payment.html',
        {
            'member': member,
            'enrollments': enrollments,
        }
    )




def paystack_callback(request):

    reference = request.GET.get('reference')

    if not reference:
        messages.error(request, 'Payment reference is missing.')
        return redirect('accounts:login')

    try:
        transaction_record = verify_and_credit_collection(
            reference,
            user=request.user if request.user.is_authenticated else None,
        )

        messages.success(
            request,
            'Payment verified and wallet credited successfully.'
        )

    except Exception as exc:

        messages.error(
            request,
            f'Payment verification failed: {exc}'
        )

    return redirect('wallets:member_wallet')




import hashlib
import hmac
import json


@csrf_exempt
@require_POST
def paystack_webhook(request):

    secret = getattr(
        settings,
        'PAYSTACK_SECRET_KEY',
        ''
    )

    signature = request.headers.get(
        'x-paystack-signature',
        ''
    )

    if not secret or not signature:
        return JsonResponse(
            {'error': 'Invalid signature'},
            status=401
        )

    expected_signature = hmac.new(
        secret.encode('utf-8'),
        request.body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        signature
    ):
        return JsonResponse(
            {'error': 'Invalid signature'},
            status=401
        )

    try:
        event = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )

    if event.get('event') != 'charge.success':
        return JsonResponse({'status': 'ignored'})

    reference = (
        event.get('data', {}).get('reference')
    )

    if not reference:
        return JsonResponse(
            {'error': 'Missing reference'},
            status=400
        )

    try:
        verify_and_credit_collection(reference)

    except Exception:
        return JsonResponse(
            {'error': 'Payment verification failed'},
            status=400
        )

    return JsonResponse({'status': 'success'})







