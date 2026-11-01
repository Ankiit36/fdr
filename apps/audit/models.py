"""Database models for the audit app."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """An immutable audit trail entry."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=64)
    model_name = models.CharField(max_length=128)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(default=timezone.now)
    prev_hash = models.CharField(max_length=64, blank=True, default="")
    entry_hash = models.CharField(max_length=64, blank=True, default="")

    def __str__(self):
        return f"AuditLog({self.pk})"
