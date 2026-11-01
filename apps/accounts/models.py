"""Custom user model for the AICTE Security Deposit / FDR Management Portal."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """User with portal specific roles."""

    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        OFFICER = "OFFICER", "Officer"
        INSTITUTION = "INSTITUTION", "Institution"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.ADMIN,
    )
    institution = models.ForeignKey(
        "institutions.Institution",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    def __str__(self):
        return self.email or self.username
