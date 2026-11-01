from django.conf import settings
from django.db import models
from agents.models import Agent
from django.utils import timezone


class Member(models.Model):

    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        INACTIVE = 'INACTIVE', 'Inactive'

    # Member identification
    member_no = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    # Personal information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100, blank=True)

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True
    )

    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to='members/',
        blank=True,
        null=True
    )

    # Next of kin
    next_of_kin = models.CharField(max_length=150, blank=True)
    next_of_kin_phone = models.CharField(max_length=20, blank=True)

    # Optional login account for member portal access
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='member_profile'
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )

    joined_at = models.DateField(auto_now_add=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_members'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.member_no:
            super().save(*args, **kwargs)
            self.member_no = f'MEM-{self.pk:06d}'
            super().save(update_fields=['member_no'])
        else:
            super().save(*args, **kwargs)

    @property
    def full_name(self):
        return ' '.join(
            part for part in [
                self.first_name,
                self.other_names,
                self.last_name
            ] if part
        )

    def __str__(self):
        return f'{self.member_no} - {self.full_name}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Member'
        verbose_name_plural = 'Members'


class MemberAssignment(models.Model):

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name='assignments'
    )

    agent = models.ForeignKey(
        Agent,
        on_delete=models.PROTECT,
        related_name='member_assignments'
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assignments'
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    ended_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    def end_assignment(self):
        self.is_active = False
        self.ended_at = timezone.now()
        self.save(update_fields=['is_active', 'ended_at'])

    def __str__(self):
        return f'{self.member.full_name} → {self.agent.full_name}'

    class Meta:
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['member'],
                condition=models.Q(is_active=True),
                name='unique_active_member_assignment'
            )
        ]
        verbose_name = 'Member Assignment'
        verbose_name_plural = 'Member Assignments'



