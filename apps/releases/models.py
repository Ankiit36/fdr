"""Database models for the releases app."""

from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Release(models.Model):
    """Release / discharge / refund request for a deposit."""

    class RequestType(models.TextChoices):
        RELEASE = "RELEASE", "Release"
        DISCHARGE = "DISCHARGE", "Discharge"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PAID_OUT = "PAID_OUT", "Paid Out"

    deposit = models.ForeignKey(
        "deposits.Deposit",
        on_delete=models.PROTECT,
        related_name="releases",
    )
    request_type = models.CharField(
        max_length=32,
        choices=RequestType.choices,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_releases",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_releases",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    eligibility_result = models.JSONField(default=dict)
    eligibility_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["deposit"],
                condition=models.Q(status__in=["REQUESTED", "UNDER_REVIEW", "APPROVED"]),
                name="one_active_release_per_deposit",
            )
        ]

    def __str__(self):
        return f"Release #{self.pk} - {self.deposit.reference_number} ({self.status})"
