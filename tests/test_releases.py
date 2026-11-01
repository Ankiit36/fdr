"""Tests for the release workflow, permissions, and dashboard totals."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.dashboard.services import dashboard_data
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError
from apps.institutions.models import Institution
from apps.releases.models import Release
from apps.releases.services import (
    approve_release,
    mark_paid_out,
    reject_release,
    request_release,
    start_review,
)


def _make_deposit(
    institution,
    created_by,
    status=Deposit.Status.ACTIVE,
    ref="REF-001",
    amount=Decimal("10000.00"),
):
    dep = Deposit.objects.create(
        institution=institution,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number=ref,
        bank_name="Test Bank",
        amount=amount,
        issue_date=date(2026, 1, 1),
        maturity_date=date(2026, 10, 1),
        status=status,
        verification_tier=Deposit.VerificationTier.BANK_CONFIRMED,
        created_by=created_by,
    )
    from apps.documents.models import DepositDocument
    from django.core.files.uploadedfile import SimpleUploadedFile

    DepositDocument.objects.create(
        deposit=dep,
        file=SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test document content"),
        doc_type="FDR_RECEIPT",
        uploaded_by=created_by,
    )
    return dep


# ---------------------------------------------------------------------------
# a. INSTITUTION can request a release for its own MATURED deposit.
#    Status is REQUESTED and an AuditLog "RELEASE_REQUESTED" row exists.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_institution_can_request_release_for_own_matured_deposit():
    inst = Institution.objects.create(name="Inst A", code="INSTA")
    inst_user = User.objects.create_user(
        username="inst_user_a",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    deposit = _make_deposit(inst, inst_user, status=Deposit.Status.MATURED, ref="REF-MAT-1")

    release = request_release(
        deposit=deposit,
        actor=inst_user,
        request_type=Release.RequestType.RELEASE,
        note="Matured FDR release request",
    )

    assert release.status == Release.Status.REQUESTED
    assert release.amount == deposit.amount
    assert release.requested_by == inst_user

    audit_entry = AuditLog.objects.filter(
        model_name="Release",
        object_id=release.pk,
        action="RELEASE_REQUESTED",
    ).first()
    assert audit_entry is not None
    assert audit_entry.actor == inst_user


# ---------------------------------------------------------------------------
# b. Requesting a release for a SUBMITTED deposit raises DomainError
#    and creates no Release row.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_request_release_for_submitted_deposit_raises_domain_error():
    inst = Institution.objects.create(name="Inst B", code="INSTB")
    inst_user = User.objects.create_user(
        username="inst_user_b",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    deposit = _make_deposit(inst, inst_user, status=Deposit.Status.SUBMITTED, ref="REF-SUB-1")

    with pytest.raises(DomainError) as exc_info:
        request_release(
            deposit=deposit,
            actor=inst_user,
            request_type=Release.RequestType.RELEASE,
        )

    assert "ACTIVE or MATURED" in str(exc_info.value)
    assert Release.objects.filter(deposit=deposit).count() == 0


# ---------------------------------------------------------------------------
# c. A second active release on the same deposit raises DomainError.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_second_active_release_on_same_deposit_raises_domain_error():
    inst = Institution.objects.create(name="Inst C", code="INSTC")
    inst_user = User.objects.create_user(
        username="inst_user_c",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    deposit = _make_deposit(inst, inst_user, status=Deposit.Status.MATURED, ref="REF-MAT-2")

    request_release(
        deposit=deposit,
        actor=inst_user,
        request_type=Release.RequestType.RELEASE,
    )

    with pytest.raises(DomainError) as exc_info:
        request_release(
            deposit=deposit,
            actor=inst_user,
            request_type=Release.RequestType.DISCHARGE,
        )

    assert "active release request already exists" in str(exc_info.value)
    assert Release.objects.filter(deposit=deposit).count() == 1


# ---------------------------------------------------------------------------
# d. Full path: REQUESTED -> UNDER_REVIEW -> APPROVED -> PAID_OUT,
#    each step by the correct role. Each step writes an AuditLog row.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_full_release_lifecycle_path():
    inst = Institution.objects.create(name="Inst D", code="INSTD")
    inst_user = User.objects.create_user(
        username="inst_user_d",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    officer = User.objects.create_user(
        username="officer_d",
        password="password",
        role=User.Roles.OFFICER,
    )
    admin_user = User.objects.create_user(
        username="admin_d",
        password="password",
        role=User.Roles.ADMIN,
    )
    deposit = _make_deposit(inst, inst_user, status=Deposit.Status.MATURED, ref="REF-MAT-3")

    # Step 1: Request
    release = request_release(deposit, inst_user, Release.RequestType.RELEASE)
    assert release.status == Release.Status.REQUESTED
    assert AuditLog.objects.filter(
        model_name="Release", object_id=release.pk, action="RELEASE_REQUESTED"
    ).exists()

    # Step 2: Under Review
    start_review(release, officer)
    release.refresh_from_db()
    assert release.status == Release.Status.UNDER_REVIEW
    assert AuditLog.objects.filter(
        model_name="Release", object_id=release.pk, action="RELEASE_UNDER_REVIEW"
    ).exists()

    # Step 3: Approve
    approve_release(release, officer, note="All clear for release")
    release.refresh_from_db()
    assert release.status == Release.Status.APPROVED
    assert release.reviewed_by == officer
    assert release.decision_note == "All clear for release"
    assert AuditLog.objects.filter(
        model_name="Release", object_id=release.pk, action="RELEASE_APPROVED"
    ).exists()

    # Step 4: Paid Out
    mark_paid_out(release, admin_user)
    release.refresh_from_db()
    assert release.status == Release.Status.PAID_OUT
    assert AuditLog.objects.filter(
        model_name="Release", object_id=release.pk, action="RELEASE_PAID_OUT"
    ).exists()


# ---------------------------------------------------------------------------
# e. An INSTITUTION user cannot approve (403 from the view)
#    and cannot mark paid out.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_institution_cannot_approve_or_mark_paid_out():
    inst = Institution.objects.create(name="Inst E", code="INSTE")
    inst_user = User.objects.create_user(
        username="inst_user_e",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    officer = User.objects.create_user(
        username="officer_e",
        password="password",
        role=User.Roles.OFFICER,
    )
    deposit = _make_deposit(inst, inst_user, status=Deposit.Status.MATURED, ref="REF-MAT-4")
    release = request_release(deposit, inst_user, Release.RequestType.RELEASE)
    start_review(release, officer)
    release.refresh_from_db()

    client = Client()
    client.force_login(inst_user)

    # Cannot approve via view -> 403
    approve_resp = client.post(f"/releases/{release.pk}/approve/", {"note": "Unauthorized approval"})
    assert approve_resp.status_code == 403
    release.refresh_from_db()
    assert release.status == Release.Status.UNDER_REVIEW

    # Approve properly via officer
    approve_release(release, officer, note="Official approval")
    release.refresh_from_db()

    # Cannot mark paid out via view -> 403
    paid_out_resp = client.post(f"/releases/{release.pk}/paid-out/")
    assert paid_out_resp.status_code == 403

    # Cannot mark paid out via service -> DomainError
    with pytest.raises(DomainError):
        mark_paid_out(release, inst_user)

    release.refresh_from_db()
    assert release.status == Release.Status.APPROVED


# ---------------------------------------------------------------------------
# f. An invalid transition, such as approving a REQUESTED release
#    without review, raises DomainError and changes nothing.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_invalid_transition_raises_domain_error_and_changes_nothing():
    inst = Institution.objects.create(name="Inst F", code="INSTF")
    inst_user = User.objects.create_user(
        username="inst_user_f",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    officer = User.objects.create_user(
        username="officer_f",
        password="password",
        role=User.Roles.OFFICER,
    )
    deposit = _make_deposit(inst, inst_user, status=Deposit.Status.MATURED, ref="REF-MAT-5")
    release = request_release(deposit, inst_user, Release.RequestType.RELEASE)

    with pytest.raises(DomainError):
        approve_release(release, officer, note="Skipping review")

    release.refresh_from_db()
    assert release.status == Release.Status.REQUESTED
    assert release.reviewed_by is None
    assert release.reviewed_at is None
    assert release.decision_note == ""


# ---------------------------------------------------------------------------
# g. Dashboard totals for an INSTITUTION user include only its own
#    institution's total_value and pending_approvals.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_dashboard_totals_for_institution_user():
    inst_a = Institution.objects.create(name="Inst Alpha", code="INSTALPHA")
    inst_b = Institution.objects.create(name="Inst Beta", code="INSTBETA")

    user_a = User.objects.create_user(
        username="user_alpha",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst_a,
    )
    user_b = User.objects.create_user(
        username="user_beta",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst_b,
    )

    # Inst A deposits
    dep_a1 = _make_deposit(inst_a, user_a, status=Deposit.Status.ACTIVE, ref="A1", amount=Decimal("50000.00"))
    dep_a2 = _make_deposit(inst_a, user_a, status=Deposit.Status.EXPIRING, ref="A2", amount=Decimal("30000.00"))
    dep_a3 = _make_deposit(inst_a, user_a, status=Deposit.Status.MATURED, ref="A3", amount=Decimal("20000.00"))
    dep_a4 = _make_deposit(inst_a, user_a, status=Deposit.Status.RENEWED, ref="A4", amount=Decimal("10000.00"))

    # Inst B deposits (must not be included in user_a's totals)
    dep_b1 = _make_deposit(inst_b, user_b, status=Deposit.Status.ACTIVE, ref="B1", amount=Decimal("100000.00"))

    # Release for A
    request_release(dep_a1, user_a, Release.RequestType.RELEASE)

    # Release for B
    request_release(dep_b1, user_b, Release.RequestType.RELEASE)

    data = dashboard_data(user_a)

    assert "totals" in data
    # total_value: ACTIVE (50000) + EXPIRING (30000) = 80000; MATURED and RENEWED excluded
    assert data["totals"]["total_value"] == Decimal("80000.00")
    # active_count: ACTIVE + EXPIRING = 2
    assert data["totals"]["active_count"] == 2
    # pending_approvals: only inst_a's release = 1
    assert data["totals"]["pending_approvals"] == 1
