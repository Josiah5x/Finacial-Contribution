
import requests

from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Collection
from wallets.services import credit_collection


class PaystackError(Exception):
    """Raised when a Paystack request fails."""
    pass


def get_headers():
    secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')

    if not secret_key:
        raise PaystackError('Paystack secret key is not configured.')

    return {
        'Authorization': f'Bearer {secret_key}',
        'Content-Type': 'application/json',
    }


def amount_to_kobo(amount):
    """Convert naira to kobo."""
    amount = Decimal(str(amount))
    return int(
        (amount * 100).quantize(
            Decimal('1'),
            rounding=ROUND_HALF_UP
        )
    )


def initialize_transaction(
    email,
    amount,
    reference,
    callback_url,
    metadata=None
):
    """Initialize a Paystack transaction."""

    url = f'{settings.PAYSTACK_BASE_URL}/transaction/initialize'

    payload = {
        'email': email,
        'amount': amount_to_kobo(amount),
        'currency': settings.PAYSTACK_CURRENCY,
        'reference': reference,
        'callback_url': callback_url,
        'metadata': metadata or {},
    }

    try:
        response = requests.post(
            url,
            headers=get_headers(),
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

    except requests.RequestException as exc:
        raise PaystackError(
            f'Unable to connect to Paystack: {exc}'
        ) from exc

    except ValueError as exc:
        raise PaystackError(
            'Paystack returned an invalid response.'
        ) from exc

    if not result.get('status'):
        raise PaystackError(
            result.get('message', 'Payment initialization failed.')
        )

    data = result.get('data') or {}

    if not data.get('authorization_url'):
        raise PaystackError(
            'Paystack did not return a checkout URL.'
        )

    return data


def verify_transaction(reference):
    """Verify a transaction directly with Paystack."""

    url = (
        f'{settings.PAYSTACK_BASE_URL}'
        f'/transaction/verify/{reference}'
    )

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

    except requests.RequestException as exc:
        raise PaystackError(
            f'Unable to verify payment: {exc}'
        ) from exc

    except ValueError as exc:
        raise PaystackError(
            'Paystack returned an invalid verification response.'
        ) from exc

    if not result.get('status'):
        raise PaystackError(
            result.get('message', 'Transaction verification failed.')
        )

    return result.get('data') or {}


@transaction.atomic
def verify_and_credit_collection(reference, user=None):
    """
    Verify payment with Paystack and credit the member's wallet.
    """

    payment = verify_transaction(reference)

    if payment.get('status') != 'success':
        raise PaystackError('Payment has not been completed successfully.')

    if payment.get('reference') != reference:
        raise PaystackError('Payment reference does not match.')

    collection = Collection.objects.select_for_update().get(
        paystack_reference=reference
    )

    expected_amount = Decimal(str(collection.amount))
    paid_amount = Decimal(str(payment.get('amount', 0))) / Decimal('100')

    if paid_amount != expected_amount:
        raise PaystackError('Payment amount does not match the collection.')

    if payment.get('currency') != 'NGN':
        raise PaystackError('Invalid payment currency.')

    # Prevent rejected collections from being credited.
    if collection.status == Collection.Status.REJECTED:
        raise PaystackError('This collection has been rejected.')

    # If already verified, the wallet service prevents duplicate credits.
    if collection.status != Collection.Status.VERIFIED:
        collection.status = Collection.Status.VERIFIED
        collection.verified_by = user
        collection.verified_at = timezone.now()
        collection.paystack_paid_at = timezone.now()

        collection.save(update_fields=[
            'status',
            'verified_by',
            'verified_at',
            'paystack_paid_at',
            'updated_at',
        ])

    return credit_collection(collection, user=user)
