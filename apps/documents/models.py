"""Database models for the documents app."""

from django.conf import settings
from django.db import models


class DepositDocument(models.Model):
    """An uploaded supporting document for a deposit."""

    deposit = models.ForeignKey(
        "deposits.Deposit",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    file = models.FileField(upload_to="deposit_documents/")
    doc_type = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DepositDocument({self.pk})"
