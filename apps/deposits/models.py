"""Database models for the deposits app."""

from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Deposit(models.Model):
    """A security deposit / FDR held through the portal."""

    class InstrumentType(models.TextChoices):
        FDR = "FDR", "Foreign Directorship Fund"
        SECURITY_DEPOSIT = "SECURITY_DEPOSIT", "Security Deposit"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_SCRUTINY = "UNDER_SCRUTINY", "Under Scrutiny"
        VERIFIED = "VERIFIED", "Verified"
        DISCREPANCY = "DISCREPANCY", "Discrepancy"
        ACTIVE = "ACTIVE", "Active"
        EXPIRING = "EXPIRING", "Expiring"
        MATURED = "MATURED", "Matured"
        RENEWED = "RENEWED", "Renewed"

    class VerificationSource(models.TextChoices):
        INSTITUTION_SUBMITTED = "INSTITUTION_SUBMITTED", "Institution Submitted"
        BANK_CONFIRMED = "BANK_CONFIRMED", "Bank Confirmed"

    class VerificationTier(models.TextChoices):
        BANK_CONFIRMED = "BANK_CONFIRMED", "Bank Confirmed"
        SCANNED_MANUAL = "SCANNED_MANUAL", "Scanned Manual"

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="deposits",
    )
    instrument_type = models.CharField(max_length=32, choices=InstrumentType.choices)
    reference_number = models.CharField(max_length=64)
    bank_name = models.CharField(max_length=255)
    bank_branch = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    issue_date = models.DateField()
    maturity_date = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    verification_source = models.CharField(
        max_length=32,
        choices=VerificationSource.choices,
        default=VerificationSource.INSTITUTION_SUBMITTED,
    )
    verification_tier = models.CharField(
        max_length=32,
        choices=VerificationTier.choices,
        default=VerificationTier.SCANNED_MANUAL,
    )
    lock_in_end_date = models.DateField(null=True, blank=True)
    previous_deposit = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="renewals",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_deposits",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bank_name", "reference_number"],
                name="deposit_bank_reference_unique",
            ),
        ]

    def __str__(self):
        return self.reference_number


class ScrutinyObservation(models.Model):
    """An officer note recorded while scrutinizing a deposit."""

    deposit = models.ForeignKey(
        Deposit,
        on_delete=models.CASCADE,
        related_name="scrutiny_observations",
    )
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scrutiny_observations",
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ScrutinyObservation({self.pk})"
