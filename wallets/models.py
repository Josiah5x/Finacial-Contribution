from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from members.models import Member


class Wallet(models.Model):
    member = models.OneToOneField(
        Member,
        on_delete=models.PROTECT,
        related_name='wallet',
    )
    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.member.full_name} - ₦{self.balance:,.2f}'

    class Meta:
        ordering = ['-created_at']


class WalletTransaction(models.Model):

    class TransactionType(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        DEBIT = 'DEBIT', 'Debit'

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='transactions',
    )

    # A collection can only produce one wallet credit.
    collection = models.OneToOneField(
        'collections_daily.Collection',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='wallet_transaction',
    )

    withdrawal = models.OneToOneField(
    'withdrawals.Withdrawal',
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name='wallet_transaction'
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    balance_before = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    balance_after = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    description = models.CharField(max_length=255, blank=True)

    reference = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f'{self.wallet.member.full_name} - '
            f'{self.get_transaction_type_display()} '
            f'₦{self.amount:,.2f}'
        )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'