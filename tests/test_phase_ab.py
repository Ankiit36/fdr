"""Tests for Phase B: Eligibility engine, Cross-institution duplicate check, and Hash-chained audit log."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.agent.models import AgentFinding, ReviewRun
from apps.audit.chain import verify_chain
from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError, create_deposit
from apps.documents.models import DepositDocument
from apps.institutions.models import Institution
from apps.releases.eligibility import evaluate_release_eligibility
from apps.releases.models import Release
from apps.releases.services import request_release


def _create_test_deposit(
    institution,
    user,
    status=Deposit.Status.MATURED,
    ref="DEP-AB-001",
    amount=Decimal("25000.00"),
    bank_name="State Bank of India",
    lock_in_end_date=None,
    verification_tier=Deposit.VerificationTier.BANK_CONFIRMED,
    with_document=True,
):
    dep = Deposit.objects.create(
        institution=institution,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number=ref,
        bank_name=bank_name,
        amount=amount,
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 1, 1),
        status=status,
        lock_in_end_date=lock_in_end_date,
        verification_tier=verification_tier,
        created_by=user,
    )
    if with_document:
        DepositDocument.objects.create(
            deposit=dep,
            file=SimpleUploadedFile("fdr_cert.pdf", b"%PDF-1.4 test certificate"),
            doc_type="FDR_RECEIPT",
            uploaded_by=user,
        )
    return dep


# ---------------------------------------------------------------------------
# a. Eligibility: a MATURED deposit with a document, VERIFIED tier,
#    and no lock-in is eligible; all checks pass.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_eligibility_matured_deposit_with_document_and_verified_tier_passes_all_checks():
    inst = Institution.objects.create(name="College Alpha", code="COL-A")
    user = User.objects.create_user(
        username="user_col_a",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    deposit = _create_test_deposit(
        institution=inst,
        user=user,
        status=Deposit.Status.MATURED,
        verification_tier=Deposit.VerificationTier.BANK_CONFIRMED,
        lock_in_end_date=None,
        with_document=True,
    )

    result = evaluate_release_eligibility(deposit, Release.RequestType.RELEASE)
    assert result["eligible"] is True
    assert len(result["checks"]) == 6
    for check in result["checks"]:
        assert check["passed"] is True, f"Check {check['code']} failed: {check['reason']}"


# ---------------------------------------------------------------------------
# b. Eligibility: an open CRITICAL finding blocks request_release,
#    raises DomainError, and the message names E03.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_eligibility_open_critical_finding_blocks_request_release():
    inst = Institution.objects.create(name="College Beta", code="COL-B")
    user = User.objects.create_user(
        username="user_col_b",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    deposit = _create_test_deposit(
        institution=inst,
        user=user,
        status=Deposit.Status.MATURED,
        verification_tier=Deposit.VerificationTier.BANK_CONFIRMED,
    )
    review_run = ReviewRun.objects.create(deposit=deposit, triggered_by=user)
    AgentFinding.objects.create(
        review_run=review_run,
        deposit=deposit,
        severity=AgentFinding.Severity.CRITICAL,
        category=AgentFinding.Category.MISMATCH,
        rule_code="R01",
        message="Critical amount mismatch",
        status=AgentFinding.Status.OPEN,
    )

    with pytest.raises(DomainError) as exc_info:
        request_release(deposit, user, Release.RequestType.RELEASE)

    assert "E03" in str(exc_info.value)
    assert Release.objects.filter(deposit=deposit).count() == 0


# ---------------------------------------------------------------------------
# c. Eligibility: lock_in_end_date in the future blocks with E06,
#    and nothing is created.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_eligibility_future_lock_in_end_date_blocks_with_e06():
    inst = Institution.objects.create(name="College Gamma", code="COL-G")
    user = User.objects.create_user(
        username="user_col_g",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    future_date = timezone.localdate() + timedelta(days=90)
    deposit = _create_test_deposit(
        institution=inst,
        user=user,
        status=Deposit.Status.MATURED,
        verification_tier=Deposit.VerificationTier.BANK_CONFIRMED,
        lock_in_end_date=future_date,
    )

    with pytest.raises(DomainError) as exc_info:
        request_release(deposit, user, Release.RequestType.RELEASE)

    assert "E06" in str(exc_info.value)
    assert Release.objects.filter(deposit=deposit).count() == 0


# ---------------------------------------------------------------------------
# d. Cross-institution: two deposits in different institutions with the
#    same reference_number and amount but different bank_name create one R11 finding.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_cross_institution_duplicate_creates_one_r11_finding():
    inst_1 = Institution.objects.create(name="Institution One", code="INST-1")
    inst_2 = Institution.objects.create(name="Institution Two", code="INST-2")
    user_1 = User.objects.create_user(
        username="user_inst_1",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst_1,
    )
    user_2 = User.objects.create_user(
        username="user_inst_2",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst_2,
    )

    # First deposit in Institution One
    create_deposit(
        institution=inst_1,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="SHARED-REF-999",
        bank_name="Canara Bank",
        amount=Decimal("150000.00"),
        issue_date=date(2025, 6, 1),
        maturity_date=date(2026, 6, 1),
        created_by=user_1,
    )

    findings_before = AgentFinding.objects.filter(
        rule_code__in=["R11", "R11_CROSS_INSTITUTION_DUPLICATE"]
    ).count()
    assert findings_before == 0

    # Second deposit in Institution Two: same ref & amount, different bank
    create_deposit(
        institution=inst_2,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="SHARED-REF-999",
        bank_name="Punjab National Bank",
        amount=Decimal("150000.00"),
        issue_date=date(2025, 6, 1),
        maturity_date=date(2026, 6, 1),
        created_by=user_2,
    )

    findings = AgentFinding.objects.filter(
        rule_code__in=["R11", "R11_CROSS_INSTITUTION_DUPLICATE"]
    )
    assert findings.count() == 1
    finding = findings.first()
    assert finding.severity == AgentFinding.Severity.CRITICAL
    assert finding.category == AgentFinding.Category.DUPLICATE_SUSPECT


# ---------------------------------------------------------------------------
# e. Hash chain: after 3 audit writes, verify_chain() returns ok True and checked 3.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_hash_chain_after_three_writes_is_valid_and_checked_three():
    AuditLog.objects.all().delete()
    user = User.objects.create_user(username="auditor", password="password", role=User.Roles.ADMIN)

    write_audit_log(actor=user, action="LOGIN", model_name="User", object_id=user.pk, changes={"ip": "127.0.0.1"})
    write_audit_log(actor=user, action="UPDATE_CONFIG", model_name="System", object_id=1, changes={"timeout": 300})
    write_audit_log(actor=user, action="VIEW_DASHBOARD", model_name="Dashboard", object_id=None, changes={})

    result = verify_chain()
    assert result["ok"] is True
    assert result["checked"] == 3
    assert result["broken_at_id"] is None


# ---------------------------------------------------------------------------
# f. Tamper: change the "changes" JSON of the second hashed entry directly
#    in the DB (use queryset.update), then verify_chain() returns ok False
#    and broken_at_id equals that entry's id.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_hash_chain_tamper_detected():
    AuditLog.objects.all().delete()
    user = User.objects.create_user(username="tamper_tester", password="password", role=User.Roles.ADMIN)

    write_audit_log(actor=user, action="ACTION_1", model_name="ModelA", object_id=1, changes={"v": 1})
    log_2 = write_audit_log(actor=user, action="ACTION_2", model_name="ModelB", object_id=2, changes={"v": 2})
    write_audit_log(actor=user, action="ACTION_3", model_name="ModelC", object_id=3, changes={"v": 3})

    # Tamper with the second entry directly in the DB
    AuditLog.objects.filter(pk=log_2.pk).update(changes={"v": "TAMPERED_VALUE"})

    result = verify_chain()
    assert result["ok"] is False
    assert result["broken_at_id"] == log_2.pk
    assert "hash mismatch" in result["reason"]


# ---------------------------------------------------------------------------
# g. Legacy rows: an audit row with blank hash before any hashed row
#    is counted in legacy_skipped and does not break the chain.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_hash_chain_legacy_rows_skipped_without_breaking_chain():
    AuditLog.objects.all().delete()
    user = User.objects.create_user(username="legacy_user", password="password", role=User.Roles.ADMIN)

    # Legacy row with blank prev_hash and entry_hash
    AuditLog.objects.create(
        actor=user,
        action="LEGACY_ACTION",
        model_name="LegacyModel",
        object_id=999,
        changes={"legacy": True},
        prev_hash="",
        entry_hash="",
    )

    # Hashed rows written via service
    write_audit_log(actor=user, action="MODERN_ACTION_1", model_name="Model1", object_id=10, changes={})
    write_audit_log(actor=user, action="MODERN_ACTION_2", model_name="Model2", object_id=20, changes={})

    result = verify_chain()
    assert result["ok"] is True
    assert result["legacy_skipped"] == 1
    assert result["checked"] == 2
    assert result["broken_at_id"] is None


# ---------------------------------------------------------------------------
# h. Admin-only verify page: INSTITUTION gets 403, ADMIN gets 200.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_admin_only_verify_page_access():
    inst = Institution.objects.create(name="College Delta", code="COL-D")
    inst_user = User.objects.create_user(
        username="inst_user_delta",
        password="password",
        role=User.Roles.INSTITUTION,
        institution=inst,
    )
    admin_user = User.objects.create_user(
        username="admin_user_delta",
        password="password",
        role=User.Roles.ADMIN,
    )

    client = Client()

    # INSTITUTION user receives 403 Forbidden
    client.force_login(inst_user)
    resp = client.get("/audit/verify/")
    assert resp.status_code == 403

    # ADMIN user receives 200 OK
    client.force_login(admin_user)
    resp = client.get("/audit/verify/")
    assert resp.status_code == 200
    assert "Cryptographic Audit Chain Verification" in resp.content.decode("utf-8")
