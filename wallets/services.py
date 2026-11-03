from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Wallet, WalletTransaction
from collections_daily.models import Collection


@transaction.atomic
def credit_collection(collection, user=None):

    # Lock the collection while processing it.
    collection = Collection.objects.select_for_update().get(
        pk=collection.pk
    )

    if collection.status != Collection.Status.VERIFIED:
        raise ValidationError(
            'Only verified collections can be credited.'
        )

    # Check whether this collection has already been credited.
    existing = WalletTransaction.objects.filter(
        collection=collection
    ).first()

    if existing:
        return existing

    # Get or create the member wallet.
    wallet, created = Wallet.objects.get_or_create(
        member=collection.enrollment.member
    )

    # Lock the wallet to prevent simultaneous balance updates.
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    if not wallet.is_active:
        raise ValidationError('This member wallet is inactive.')

    balance_before = wallet.balance
    balance_after = balance_before + collection.amount

    transaction_record = WalletTransaction.objects.create(
        wallet=wallet,
        collection=collection,
        transaction_type=WalletTransaction.TransactionType.CREDIT,
        amount=collection.amount,
        balance_before=balance_before,
        balance_after=balance_after,
        description=f'Contribution payment - {collection.receipt_no}',
        reference=f'WLT-{collection.pk:08d}',
        created_by=user,
    )

    wallet.balance = balance_after
    wallet.save(update_fields=['balance', 'updated_at'])

    return transaction_record