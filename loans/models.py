
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class Loan(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        DISBURSED = 'DISBURSED', 'Disbursed'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'

    loan_no = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    member = models.ForeignKey(
        'members.Member',
        on_delete=models.PROTECT,
        related_name='loans'
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='loan_applications'
    )

    # Eligibility snapshot when the application is submitted
    verified_contributions = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    eligibility_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('25.00')
    )

    eligible_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    requested_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    approved_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    repayment_months = models.PositiveSmallIntegerField(
        default=1
    )

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[
            MinValueValidator(Decimal('0.01'))
        ],
        help_text='Annual interest rate in percentage.'
        )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_loans'
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
        related_name='rejected_loans'
    )

    rejection_reason = models.TextField(blank=True)

    disbursed_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    disbursement_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True
    )

    disbursement_reference = models.CharField(
        max_length=100,
        blank=True
    )

    disbursed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disbursed_loans'
    )

    disbursed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.loan_no:
            super().save(*args, **kwargs)
            self.loan_no = f'LN-{self.pk:06d}'
            super().save(update_fields=['loan_no'])
        else:
            super().save(*args, **kwargs)

    @property
    def total_repaid(self):
        return self.repayments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

    # @property
    # def outstanding_balance(self):
    #     principal = self.disbursed_amount or self.approved_amount or Decimal('0.00')
    #     return max(principal - self.total_repaid, Decimal('0.00'))



    @property
    def principal_amount(self):
        return (
            self.disbursed_amount
            or self.approved_amount
            or Decimal('0.00')
        )


    @property
    def total_interest(self):
        """
        Simple interest calculated annually.
        """
        principal = self.principal_amount

        interest = (
            principal
            * self.interest_rate
            * Decimal(self.repayment_months)
            / Decimal('1200')
        )

        return interest.quantize(Decimal('0.01'))


    @property
    def total_repayable(self):
        return self.principal_amount + self.total_interest


    @property
    def monthly_installment(self):
        if not self.repayment_months:
            return Decimal('0.00')

        return (
            self.total_repayable / self.repayment_months
        ).quantize(Decimal('0.01'))


    @property
    def outstanding_balance(self):
        return max(
            self.total_repayable - self.total_repaid,
            Decimal('0.00')
        )

    def clean(self):
        errors = {}

        if self.requested_amount and self.eligible_amount:
            if self.requested_amount > self.eligible_amount:
                errors['requested_amount'] = (
                    'Requested amount cannot exceed your eligible loan amount.'
                )

        if self.approved_amount is not None:
            if self.approved_amount <= 0:
                errors['approved_amount'] = 'Approved amount must be greater than zero.'
            elif self.approved_amount > self.eligible_amount:
                errors['approved_amount'] = 'Approved amount cannot exceed eligibility.'

        if self.repayment_months < 1:
            errors['repayment_months'] = 'Repayment period must be at least one month.'

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.loan_no} - {self.member}'


# /////////////////////////////////////////

class LoanRepayment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'

    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name='repayments'
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )

    reference = models.CharField(
        max_length=100,
        blank=True
    )

    repayment_date = models.DateField()

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='received_loan_repayments'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.loan.loan_no} - ₦{self.amount:,.2f}'

    class Meta:
        ordering = ['-repayment_date', '-created_at']
