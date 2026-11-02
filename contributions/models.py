from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from members.models import Member


class ContributionPlan(models.Model):

    class Frequency(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'

    WEEKDAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)

    description = models.TextField(blank=True)

    frequency = models.CharField(
        max_length=10,
        choices=Frequency.choices,
        default=Frequency.DAILY
    )

    # Amount payable at each collection
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    # Used for weekly plans
    collection_weekday = models.IntegerField(
        choices=WEEKDAYS,
        null=True,
        blank=True
    )

    # Used for monthly plans (1-28)
    collection_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    # Optional plan duration
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Leave empty for an ongoing contribution plan."
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_contribution_plans'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if self.frequency == self.Frequency.WEEKLY:
            if self.collection_weekday is None:
                errors['collection_weekday'] = (
                    'Select the collection weekday.'
                )

        elif self.frequency != self.Frequency.WEEKLY:
            self.collection_weekday = None

        if self.frequency == self.Frequency.MONTHLY:
            if self.collection_day is None:
                errors['collection_day'] = (
                    'Enter the monthly collection day.'
                )
            elif not 1 <= self.collection_day <= 28:
                errors['collection_day'] = (
                    'Collection day must be between 1 and 28.'
                )

        elif self.frequency != self.Frequency.MONTHLY:
            self.collection_day = None

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.name} - ₦{self.amount} ({self.get_frequency_display()})'

    class Meta:
        ordering = ['name']
        verbose_name = 'Contribution Plan'
        verbose_name_plural = 'Contribution Plans'






class PlanEnrollment(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name='plan_enrollments'
    )

    plan = models.ForeignKey(
        ContributionPlan,
        on_delete=models.PROTECT,
        related_name='enrollments'
    )

    # Snapshot of the agreed amount when the member enrols.
    # Later changes to the plan amount won't change this enrolment.
    agreed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    start_date = models.DateField(default=timezone.localdate)

    end_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    enrolled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_enrollments'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End date cannot be before the start date.'
            })

        if self.plan_id and not self.plan.is_active and not self.pk:
            raise ValidationError({
                'plan': 'You cannot enrol a member in an inactive plan.'
            })

    def __str__(self):
        return f'{self.member.full_name} - {self.plan.name}'

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'plan'],
                condition=models.Q(status='ACTIVE'),
                name='unique_active_member_plan'
            )
        ]
        verbose_name = 'Plan Enrolment'
        verbose_name_plural = 'Plan Enrolments'



