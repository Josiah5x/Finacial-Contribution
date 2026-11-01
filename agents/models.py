from django.conf import settings
from django.db import models


class Agent(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    agent_no = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='agent_profile'
    )

    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    collection_area = models.CharField(max_length=150)

    daily_target = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    employment_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.agent_no:
            super().save(*args, **kwargs)
            self.agent_no = f'AGT-{self.pk:05d}'
            super().save(update_fields=['agent_no'])
        else:
            super().save(*args, **kwargs)

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return f'{self.agent_no} - {self.full_name}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'