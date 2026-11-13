
from django.contrib.auth.models import AbstractUser
from django.db import models

from django.utils import timezone


class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        MANAGER = 'MANAGER', 'Manager'
        SUPERVISOR = 'SUPERVISOR', 'Supervisor'
        AGENT = 'AGENT', 'Collection Agent'
        ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
        MEMBER = 'MEMBER', 'Member'

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )

    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser




class EmailOTP(models.Model):

    email = models.EmailField(db_index=True)

    # Store a hashed OTP, never the plain six-digit code.
    otp_hash = models.CharField(max_length=128)

    expires_at = models.DateTimeField()

    attempts = models.PositiveSmallIntegerField(default=0)

    is_used = models.BooleanField(default=False)

    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    MAX_ATTEMPTS = 5

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_valid(self):
        return (
            not self.is_used
            and not self.is_expired()
            and self.attempts < self.MAX_ATTEMPTS
        )

    def __str__(self):
        return f'OTP for {self.email}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'
