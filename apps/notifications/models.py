"""Database models for the notifications app."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """An in-app or email notification for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    deposit = models.ForeignKey(
        "deposits.Deposit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification({self.pk})"


class ReminderLog(models.Model):
    """Log of reminder dispatch attempts."""

    DEPOSIT = "DEPOSIT"
    MATURITY = "MATURITY"

    DEPOSIT_TYPES = (
        (DEPOSIT, "Deposit"),
        (MATURITY, "Maturity"),
    )

    CHANNEL_CHOICES = (
        ("EMAIL", "Email"),
        ("IN_APP", "In App"),
        ("SMS", "SMS"),
        ("WHATSAPP", "WhatsApp"),
    )

    deposit = models.ForeignKey(
        "deposits.Deposit",
        on_delete=models.CASCADE,
        related_name="reminder_logs",
    )
    reminder_type = models.CharField(max_length=64, choices=DEPOSIT_TYPES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deposit", "reminder_type", "channel"],
                name="reminder_log_unique_deposit_type_channel",
            ),
        ]

    def __str__(self):
        return f"ReminderLog({self.pk})"
