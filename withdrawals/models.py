
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from members.models import Member


class Withdrawal(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        PAID = 'PAID', 'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'

    request_no = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name='withdrawals'
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='withdrawal_requests'
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_withdrawals'
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_withdrawals'
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True
    )

    rejection_reason = models.TextField(blank=True)

    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_withdrawals'
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.request_no:
            super().save(*args, **kwargs)
            self.request_no = f'WD-{self.pk:06d}'
            super().save(update_fields=['request_no'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.request_no} - {self.member.full_name}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Withdrawal'
        verbose_name_plural = 'Withdrawals'
