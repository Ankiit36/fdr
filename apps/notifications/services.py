"""Notification services: recipients, reminders, in-app, email, and maturity alerts."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import write_audit_log
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError, change_status, get_maturity_status
from apps.notifications.models import Notification, ReminderLog

logger = logging.getLogger(__name__)


def recipients_for(deposit):
    """Return active users who should receive notifications for a deposit.

    Includes all active INSTITUTION users of the deposit's institution
    plus all active OFFICER users.
    """
    institution_users = User.objects.filter(
        role=User.Roles.INSTITUTION,
        institution=deposit.institution,
        is_active=True,
    )
    officer_users = User.objects.filter(
        role=User.Roles.OFFICER,
        is_active=True,
    )
    return (institution_users | officer_users).distinct()


def record_reminder(deposit, reminder_type, channel):
    """Record a reminder in ReminderLog.

    Returns True only if a new row was created (idempotent via unique constraint).
    """
    _, created = ReminderLog.objects.get_or_create(
        deposit=deposit,
        reminder_type=reminder_type,
        channel=channel,
    )
    return created


def create_in_app(user, deposit, message):
    """Create an in-app Notification for a user."""
    return Notification.objects.create(
        user=user,
        deposit=deposit,
        message=message,
    )


def send_email_reminder(deposit, subject, body):
    """Send an email reminder to the deposit's institution contact email.

    If the contact email is empty, log a warning and skip.
    """
    contact_email = deposit.institution.contact_email
    if not contact_email:
        logger.warning(
            "Skipping email reminder for deposit %s: no contact email on institution %s",
            deposit.reference_number,
            deposit.institution.name,
        )
        return
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[contact_email],
        fail_silently=False,
    )


def escalate_stale_findings():
    """Find deposits with critical findings open longer than AGENT_ESCALATION_DAYS.

    For each such deposit, records a reminder for each channel ('IN_APP', 'EMAIL', 'SMS', 'WHATSAPP').
    If newly recorded, dispatches notifications to OFFICER and ADMIN in-app and via EmailChannel,
    SmsMockChannel, and WhatsAppMockChannel.
    Returns {"escalated": n}.
    """
    from apps.agent.models import AgentFinding
    from apps.notifications.channels import EmailChannel, SmsMockChannel, WhatsAppMockChannel

    escalation_days = settings.AGENT_ESCALATION_DAYS
    cutoff = timezone.now() - timedelta(days=escalation_days)

    stale_deposit_ids = (
        AgentFinding.objects.filter(
            status=AgentFinding.Status.OPEN,
            severity=AgentFinding.Severity.CRITICAL,
            created_at__lt=cutoff,
        )
        .values_list("deposit_id", flat=True)
        .distinct()
    )

    stale_deposits = Deposit.objects.filter(pk__in=stale_deposit_ids).select_related("institution")

    escalated = 0
    email_channel = EmailChannel()
    sms_channel = SmsMockChannel()
    whatsapp_channel = WhatsAppMockChannel()

    officer_and_admin_users = list(
        User.objects.filter(
            role__in=[User.Roles.OFFICER, User.Roles.ADMIN],
            is_active=True,
        )
    )

    for deposit in stale_deposits:
        recorded_any = False
        for channel in ("IN_APP", "EMAIL", "SMS", "WHATSAPP"):
            if record_reminder(deposit, "FINDING_ESCALATION", channel):
                recorded_any = True

        if recorded_any:
            subject = f"Escalation: Unresolved critical finding on {deposit.reference_number}"
            body = (
                f"Deposit {deposit.reference_number} ({deposit.institution.name}) "
                f"has one or more CRITICAL findings that have remained OPEN for more than "
                f"{escalation_days} days. Immediate review required."
            )
            msg = f"Escalation: {deposit.reference_number} has unresolved critical findings over {escalation_days} days old."
            for user in officer_and_admin_users:
                create_in_app(user, deposit, msg)

            recipient = deposit.institution.contact_email or "officer@aicte.local"
            email_channel.send(recipient, subject, body)
            sms_channel.send(recipient, subject, body)
            whatsapp_channel.send(recipient, subject, body)

            escalated += 1

    return {"escalated": escalated}


def run_maturity_alerts():
    """Run maturity alert processing for all deposits.

    Returns a dict with keys:
        status_updated -- number of deposits whose status was transitioned
        reminders_sent -- number of reminder dispatches actually sent
        skipped        -- number of deposits skipped due to DomainError
        escalated      -- number of deposits whose stale critical findings were escalated
    """
    status_updated = 0
    reminders_sent = 0
    skipped = 0

    today = timezone.localdate()

    deposits = (
        Deposit.objects.filter(
            status__in=[
                Deposit.Status.ACTIVE,
                Deposit.Status.EXPIRING,
                Deposit.Status.MATURED,
            ]
        )
        .select_related("institution")
        .order_by("pk")
    )

    for deposit in deposits:
        state = get_maturity_status(deposit, today=today)

        new_status = None
        if state == Deposit.Status.EXPIRING and deposit.status == Deposit.Status.ACTIVE:
            new_status = Deposit.Status.EXPIRING
        elif (
            state == Deposit.Status.MATURED
            and deposit.status in (Deposit.Status.ACTIVE, Deposit.Status.EXPIRING)
        ):
            new_status = Deposit.Status.MATURED

        if new_status is not None:
            try:
                change_status(deposit, new_status, actor=None, audit_action="MATURITY_ALERT")
                status_updated += 1
            except DomainError:
                skipped += 1
                continue

        current_status = deposit.status
        if current_status == Deposit.Status.EXPIRING:
            reminder_type = "MATURITY_SOON"
        elif current_status == Deposit.Status.MATURED:
            reminder_type = "MATURED"
        else:
            reminder_type = None

        if reminder_type is not None:
            for channel in ("IN_APP", "EMAIL"):
                if not record_reminder(deposit, reminder_type, channel):
                    continue

                if channel == "IN_APP":
                    message = f"Deposit {deposit.reference_number} is {current_status.lower()}."
                    for user in recipients_for(deposit):
                        create_in_app(user, deposit, message)
                    reminders_sent += 1
                else:  # EMAIL
                    subject = f"FDR Alert: {deposit.reference_number} is {current_status}"
                    body = (
                        f"Dear {deposit.institution.name},\n\n"
                        f"Your deposit {deposit.reference_number} "
                        f"is now {current_status.lower()}.\n"
                        f"Maturity date: {deposit.maturity_date}\n"
                        f"Amount: {deposit.amount}\n\n"
                        f"Regards,\nFDR Portal"
                    )
                    try:
                        send_email_reminder(deposit, subject, body)
                    except Exception:
                        pass
                    reminders_sent += 1

    escalation_result = escalate_stale_findings()
    escalated_count = escalation_result.get("escalated", 0)

    return {
        "status_updated": status_updated,
        "reminders_sent": reminders_sent,
        "skipped": skipped,
        "escalated": escalated_count,
    }
