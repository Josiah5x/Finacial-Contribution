from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from contributions.models import PlanEnrollment
from members.models import MemberAssignment


class Collection(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
        PAYSTACK = 'PAYSTACK', 'Paystack Online Payment'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Verification'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    receipt_no = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )
    

    enrollment = models.ForeignKey(
        PlanEnrollment,
        on_delete=models.PROTECT,
        related_name='collections'
    )

    # Preserve the agent assignment that was active when payment was recorded.
    assignment = models.ForeignKey(
        MemberAssignment,
        on_delete=models.PROTECT,
        related_name='collections'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )

    transaction_reference = models.CharField(
        max_length=100,
        blank=True
    )

    paystack_reference = models.CharField(
    max_length=100,
    unique=True,
    null=True,
    blank=True
    )

    paystack_access_code = models.CharField(
        max_length=100,
        blank=True
    )

    paystack_authorization_url = models.URLField(
        max_length=500,
        blank=True
    )

    paystack_paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    collection_date = models.DateField(
        default=timezone.localdate
    )

    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recorded_collections'
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_collections',
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_collections',
    )
    rejected_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()

        errors = {}

        if self.enrollment_id and self.assignment_id:
            if self.enrollment.member_id != self.assignment.member_id:
                errors['assignment'] = (
                    'The selected agent assignment does not belong to this member.'
                )

        if self.enrollment_id:
            if self.enrollment.status != PlanEnrollment.Status.ACTIVE:
                errors['enrollment'] = (
                    'Collections can only be recorded for active enrolments.'
                )

        if self.payment_method == self.PaymentMethod.BANK_TRANSFER:
            if not self.transaction_reference.strip():
                errors['transaction_reference'] = (
                    'Enter the bank transfer reference.'
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            super().save(*args, **kwargs)

            self.receipt_no = f'DC-{self.collection_date:%Y%m%d}-{self.pk:06d}'

            super().save(update_fields=['receipt_no'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.receipt_no or "New Receipt"} - ₦{self.amount}'

    class Meta:
        ordering = ['-collection_date', '-created_at']
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'