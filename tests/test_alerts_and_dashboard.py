"""Alerts and dashboard tests."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.dashboard.services import dashboard_data
from apps.deposits.models import Deposit
from apps.institutions.models import Institution
from apps.notifications.models import Notification, ReminderLog
from apps.notifications.services import run_maturity_alerts


def _make_user(role, institution=None):
    username = f"{role.lower()}_{institution.code if institution else 'none'}"
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role,
        institution=institution,
    )


def _make_deposit(institution, created_by, status=Deposit.Status.ACTIVE, maturity_offset_days=-1):
    return Deposit.objects.create(
        institution=institution,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number=f"REF-{institution.code}-{status}",
        bank_name=f"Bank {institution.code}",
        amount=10000.00,
        issue_date=date(2026, 1, 1),
        maturity_date=date.today() + timedelta(days=maturity_offset_days),
        status=status,
        created_by=created_by,
    )


# ---------------------------------------------------------------------------
# Test a: Running run_maturity_alerts twice is idempotent
# ---------------------------------------------------------------------------
@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_run_maturity_alerts_idempotent():
    institution = Institution.objects.create(
        name="Inst A", code="INSTA", contact_email="admin@insta.example.com"
    )
    officer = _make_user(User.Roles.OFFICER)

    # Deposit with status ACTIVE and maturity within reminder window -> EXPIRING
    deposit = _make_deposit(
        institution, officer, status=Deposit.Status.ACTIVE, maturity_offset_days=5
    )

    # First run
    mail.outbox.clear()
    result1 = run_maturity_alerts()
    reminders_after_first = ReminderLog.objects.count()
    notifications_after_first = Notification.objects.count()
    emails_after_first = len(mail.outbox)

    assert result1["status_updated"] >= 1
    assert reminders_after_first >= 2  # IN_APP + EMAIL
    assert notifications_after_first >= 1
    assert emails_after_first >= 1

    # Second run - should be idempotent
    result2 = run_maturity_alerts()
    reminders_after_second = ReminderLog.objects.count()
    notifications_after_second = Notification.objects.count()
    emails_after_second = len(mail.outbox)

    assert result2["reminders_sent"] == 0
    assert ReminderLog.objects.count() == reminders_after_first
    assert Notification.objects.count() == notifications_after_first
    assert len(mail.outbox) == emails_after_first


# ---------------------------------------------------------------------------
# Test b: INSTITUTION user's dashboard_data counts only own institution
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_dashboard_data_institution_scoped():
    institution_a = Institution.objects.create(name="Inst A", code="INSTA")
    institution_b = Institution.objects.create(name="Inst B", code="INSTB")
    officer = _make_user(User.Roles.OFFICER)

    # Deposits in institution A
    _make_deposit(institution_a, officer, status=Deposit.Status.ACTIVE)
    _make_deposit(institution_a, officer, status=Deposit.Status.EXPIRING)
    # Deposit in institution B
    _make_deposit(institution_b, officer, status=Deposit.Status.ACTIVE)

    user_a = _make_user(User.Roles.INSTITUTION, institution_a)
    data = dashboard_data(user_a)

    # Should only see institution A's deposits
    assert data["counts"]["active"] == 1
    assert data["counts"]["expiring"] == 1
    assert data["counts"]["matured"] == 0
    assert data["counts"]["renewed"] == 0
    assert data["counts"]["pending_verification"] == 0

    # Upcoming maturities should only include institution A's deposits
    for dep in data["upcoming_maturities"]:
        assert dep.institution_id == institution_a.pk

    # Pending verifications should only include institution A's deposits
    for dep in data["pending_verifications"]:
        assert dep.institution_id == institution_a.pk


# ---------------------------------------------------------------------------
# Test c: AuditLogListView returns 403 for INSTITUTION, 200 for ADMIN
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_audit_log_view_permissions():
    institution = Institution.objects.create(name="Inst", code="INSTX")
    institution_user = _make_user(User.Roles.INSTITUTION, institution)
    admin_user = _make_user(User.Roles.ADMIN)

    client = Client()

    # INSTITUTION user gets 403
    client.force_login(institution_user)
    response = client.get(reverse("audit:audit_log_list"))
    assert response.status_code == 403

    # ADMIN user gets 200
    client.force_login(admin_user)
    response = client.get(reverse("audit:audit_log_list"))
    assert response.status_code == 200