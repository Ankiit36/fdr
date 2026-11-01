"""Notification delivery channels (Email and mock SMS/WhatsApp)."""

import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base channel for dispatching notifications."""

    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> bool:
        """Send notification to the recipient. Return True on success."""
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    """Email delivery channel using Django send_mail."""

    def send(self, recipient: str, subject: str, body: str) -> bool:
        if not recipient:
            logger.warning("EmailChannel skipped: empty recipient")
            return False
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            return True
        except Exception as exc:
            logger.error("EmailChannel failed to send to %s: %s", recipient, exc)
            return False


class SmsMockChannel(NotificationChannel):
    """Mock SMS channel for development and tests."""

    def send(self, recipient: str, subject: str, body: str) -> bool:
        logger.info("[MOCK SMS] To: %s | Subject: %s | Body: %s", recipient, subject, body)
        return True


class WhatsAppMockChannel(NotificationChannel):
    """Mock WhatsApp channel for development and tests."""

    def send(self, recipient: str, subject: str, body: str) -> bool:
        logger.info("[MOCK WHATSAPP] To: %s | Subject: %s | Body: %s", recipient, subject, body)
        return True
