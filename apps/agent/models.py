from django.conf import settings
from django.db import models


class ReviewRun(models.Model):
    """A single agent review run for a deposit."""

    deposit = models.ForeignKey(
        "deposits.Deposit",
        on_delete=models.CASCADE,
        related_name="agent_review_runs",
    )
    run_at = models.DateTimeField(auto_now_add=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="agent_review_runs",
    )

    def __str__(self):
        return f"ReviewRun({self.pk})"


class ExtractedField(models.Model):
    """A single field extracted by the agent during a review run."""

    class ExtractionStatus(models.TextChoices):
        OK = "OK", "OK"
        NOT_FOUND = "NOT_FOUND", "Not Found"
        NO_TEXT_LAYER = "NO_TEXT_LAYER", "No Text Layer"

    review_run = models.ForeignKey(
        ReviewRun,
        on_delete=models.CASCADE,
        related_name="extracted_fields",
    )
    deposit = models.ForeignKey(
        "deposits.Deposit",
        on_delete=models.CASCADE,
        related_name="extracted_fields",
    )
    document = models.ForeignKey(
        "documents.DepositDocument",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="extracted_fields",
    )
    field_name = models.CharField(max_length=64)
    extracted_value = models.TextField()
    source_snippet = models.TextField(blank=True)
    extraction_status = models.CharField(
        max_length=20,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.OK,
    )

    def __str__(self):
        return f"ExtractedField({self.pk})"


class AgentFinding(models.Model):
    """A rule based finding produced by the agent for a deposit."""

    class Severity(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    class Category(models.TextChoices):
        MISMATCH = "MISMATCH", "Mismatch"
        MISSING_DATA = "MISSING_DATA", "Missing Data"
        NO_TEXT_LAYER = "NO_TEXT_LAYER", "No Text Layer"
        MATURITY_SOON = "MATURITY_SOON", "Maturity Soon"
        MATURED = "MATURED", "Matured"
        DUPLICATE_SUSPECT = "DUPLICATE_SUSPECT", "Duplicate Suspect"
        RENEWAL_DUE = "RENEWAL_DUE", "Renewal Due"
        FORGERY_SUSPECT = "FORGERY_SUSPECT", "Forgery Suspect"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"

    review_run = models.ForeignKey(
        ReviewRun,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    deposit = models.ForeignKey(
        "deposits.Deposit",
        on_delete=models.CASCADE,
        related_name="agent_findings",
    )
    severity = models.CharField(max_length=20, choices=Severity.choices)
    category = models.CharField(max_length=20, choices=Category.choices)
    message = models.TextField()
    rule_code = models.CharField(max_length=16)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_agent_findings",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolution_note = models.TextField(blank=True)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deposit", "rule_code"],
                condition=models.Q(status="OPEN"),
                name="one_open_agent_finding_per_deposit_rule",
            ),
        ]

    def __str__(self):
        return f"AgentFinding({self.pk})"
