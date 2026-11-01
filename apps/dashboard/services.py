"""Dashboard service: aggregates data for the dashboard view."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.accounts.permissions import is_admin, is_institution_user, is_officer
from apps.agent.messages_hi import render_finding_message
from apps.agent.models import AgentFinding
from apps.agent.services import priority_score
from apps.deposits.models import Deposit
from apps.deposits.services import get_visible_deposits
from apps.notifications.models import Notification
from apps.releases.models import Release


def dashboard_data(user, lang: str = "en"):
    """Return dashboard data for the given user, scoped by role/institution."""

    def scope_deposits():
        return get_visible_deposits(user)

    deposits = scope_deposits()
    now = timezone.localdate()
    reminder_window = settings.REMINDER_WINDOW_DAYS

    counts = {
        "active": deposits.filter(status=Deposit.Status.ACTIVE).count(),
        "expiring": deposits.filter(status=Deposit.Status.EXPIRING).count(),
        "matured": deposits.filter(status=Deposit.Status.MATURED).count(),
        "renewed": deposits.filter(status=Deposit.Status.RENEWED).count(),
        "pending_verification": deposits.filter(
            status__in=[Deposit.Status.SUBMITTED, Deposit.Status.UNDER_SCRUTINY]
        ).count(),
    }

    # Dashboard totals
    total_value = deposits.exclude(
        status__in=[Deposit.Status.RENEWED, Deposit.Status.MATURED]
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(Decimal("0")))
    )["total"]

    active_count = deposits.filter(
        status__in=[Deposit.Status.ACTIVE, Deposit.Status.EXPIRING]
    ).count()

    if is_admin(user) or is_officer(user):
        pending_approvals = Release.objects.filter(
            status__in=[Release.Status.REQUESTED, Release.Status.UNDER_REVIEW]
        ).count()
    elif is_institution_user(user) and getattr(user, "institution_id", None):
        pending_approvals = Release.objects.filter(
            deposit__institution_id=user.institution_id,
            status__in=[Release.Status.REQUESTED, Release.Status.UNDER_REVIEW],
        ).count()
    else:
        pending_approvals = 0

    totals = {
        "total_value": total_value,
        "active_count": active_count,
        "pending_approvals": pending_approvals,
    }

    upcoming_maturities = deposits.filter(
        maturity_date__range=[now, now + timedelta(days=reminder_window)]
    ).order_by("maturity_date")[:10]

    pending_verifications = deposits.filter(
        status__in=[Deposit.Status.SUBMITTED, Deposit.Status.UNDER_SCRUTINY]
    ).order_by("-created_at")[:10]

    unread_notifications = {
        "count": Notification.objects.filter(user=user, is_read=False).count(),
        "latest": Notification.objects.filter(user=user, is_read=False)
        .order_by("-created_at")[:5],
    }

    # Top 10 OPEN findings sorted by priority_score, scoped to visible deposits.
    visible_deposit_pks = set(deposits.values_list("pk", flat=True))
    findings = AgentFinding.objects.filter(
        status=AgentFinding.Status.OPEN,
        deposit__pk__in=visible_deposit_pks,
    ).order_by("-created_at")[:10]

    top_findings = sorted(findings, key=priority_score, reverse=True)[:10]
    for finding in top_findings:
        finding.display_message = render_finding_message(finding, lang)

    return {
        "reminder_window": reminder_window,
        "counts": counts,
        "totals": totals,
        "upcoming_maturities": upcoming_maturities,
        "pending_verifications": pending_verifications,
        "unread_notifications": unread_notifications,
        "top_findings": top_findings,
    }


def analytics_by_institution(user):
    """Aggregate per-institution statistics scoped by user visibility."""
    from apps.institutions.models import Institution

    visible_deposits = get_visible_deposits(user)

    if is_admin(user) or is_officer(user):
        institutions = Institution.objects.all().order_by("name")
    elif is_institution_user(user) and getattr(user, "institution_id", None):
        institutions = Institution.objects.filter(pk=user.institution_id)
    else:
        institutions = Institution.objects.none()

    results = []
    for inst in institutions:
        inst_deposits = visible_deposits.filter(institution=inst)
        total_deposits = inst_deposits.count()
        expiring_count = inst_deposits.filter(status=Deposit.Status.EXPIRING).count()
        matured_count = inst_deposits.filter(status=Deposit.Status.MATURED).count()
        discrepancy_count = inst_deposits.filter(status=Deposit.Status.DISCREPANCY).count()
        critical_findings_count = AgentFinding.objects.filter(
            deposit__in=inst_deposits,
            status=AgentFinding.Status.OPEN,
            severity=AgentFinding.Severity.CRITICAL,
        ).count()
        total_value = inst_deposits.aggregate(
            val=Coalesce(Sum("amount"), Value(Decimal("0.00")))
        )["val"]

        results.append({
            "name": inst.name,
            "code": inst.code,
            "total_deposits": total_deposits,
            "expiring_count": expiring_count,
            "matured_count": matured_count,
            "discrepancy_count": discrepancy_count,
            "critical_findings_count": critical_findings_count,
            "total_value": total_value,
        })

    return results
