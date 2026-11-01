"""Agent phase tests: extraction, rules, services, actions, views."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.agent.actions import apply_suggestion
from apps.agent.extraction import extract_from_file
from apps.agent.models import AgentFinding
from apps.agent.services import run_review_for_deposit
from apps.audit.models import AuditLog
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError
from apps.documents.services import upload_document
from apps.institutions.models import Institution


from apps.agent.synthetic import build_text_pdf

_make_pdf_bytes = build_text_pdf


def _make_deposit(institution, created_by, status=Deposit.Status.SUBMITTED):
    return Deposit.objects.create(
        institution=institution,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="FDR123456",
        bank_name="State Bank of India",
        amount=Decimal("50000.00"),
        issue_date=date(2026, 4, 1),
        maturity_date=date(2027, 4, 1),
        status=status,
        created_by=created_by,
    )


# ---------------------------------------------------------------------------
# Test a: Extraction from text-layer PDF
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_extraction_reads_text_layer_pdf():
    institution = Institution.objects.create(name="Inst", code="INST1")
    officer = User.objects.create_user(
        username="officer_a", password="pw", role=User.Roles.OFFICER
    )
    deposit = _make_deposit(institution, officer)

    pdf_bytes = _make_pdf_bytes(
        [
            "Reference No: FDR123456",
            "Amount: Rs. 50,000",
            "Issue Date: 01/04/2026",
            "Maturity Date: 01/04/2027",
            "Bank Name: State Bank of India",
        ]
    )
    uploaded = SimpleUploadedFile("fdr.pdf", pdf_bytes, content_type="application/pdf")
    document = upload_document(deposit, uploaded, "FDR_CERTIFICATE", officer)

    text, fields = extract_from_file(document.file.path)
    field_map = {f.field_name: f for f in fields}

    assert field_map["reference_number"].extraction_status == "OK"
    assert field_map["reference_number"].extracted_value == "FDR123456"
    assert field_map["amount"].extraction_status == "OK"
    assert "50,000" in field_map["amount"].extracted_value
    assert field_map["issue_date"].extraction_status == "OK"
    assert field_map["maturity_date"].extraction_status == "OK"
    assert field_map["bank_name"].extraction_status == "OK"


# ---------------------------------------------------------------------------
# Test b: Image upload -> NO_TEXT_LAYER, no pytesseract imported
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_image_upload_no_text_layer_no_ocr():
    assert "pytesseract" not in sys.modules

    institution = Institution.objects.create(name="Inst", code="INST2")
    officer = User.objects.create_user(
        username="officer_b", password="pw", role=User.Roles.OFFICER
    )
    deposit = _make_deposit(institution, officer)

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    uploaded = SimpleUploadedFile("scan.png", png_bytes, content_type="image/png")
    document = upload_document(deposit, uploaded, "FDR_CERTIFICATE", officer)

    text, fields = extract_from_file(document.file.path)
    assert text == ""
    for field in fields:
        assert field.extraction_status == "NO_TEXT_LAYER"

    assert "pytesseract" not in sys.modules


# ---------------------------------------------------------------------------
# Test c: AMOUNT_MISMATCH fires when extracted amount differs
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_amount_mismatch_fires():
    from apps.agent.rules import RULE_BY_CODE

    institution = Institution.objects.create(name="Inst", code="INST3")
    officer = User.objects.create_user(
        username="officer_c", password="pw", role=User.Roles.OFFICER
    )
    deposit = _make_deposit(institution, officer)

    field_map = {
        "amount": type(
            "FE",
            (),
            {
                "extraction_status": "OK",
                "extracted_value": "99,999.00",
                "source_snippet": "Amount: Rs. 99,999",
            },
        )()
    }

    result = RULE_BY_CODE["R01"](deposit, field_map)
    assert result.should_create is True
    assert result.severity == "CRITICAL"
    assert result.rule_code == "R01"


# ---------------------------------------------------------------------------
# Test d: Running review twice leaves exactly one OPEN finding per rule_code
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_review_twice_one_open_finding_per_rule():
    institution = Institution.objects.create(name="Inst", code="INST4")
    officer = User.objects.create_user(
        username="officer_d", password="pw", role=User.Roles.OFFICER
    )
    deposit = _make_deposit(institution, officer)

    run_review_for_deposit(deposit, triggered_by=officer)
    open_count_after_first = AgentFinding.objects.filter(
        deposit=deposit, status=AgentFinding.Status.OPEN
    ).count()
    assert open_count_after_first >= 1

    run_review_for_deposit(deposit, triggered_by=officer)
    open_count_after_second = AgentFinding.objects.filter(
        deposit=deposit, status=AgentFinding.Status.OPEN
    ).count()
    assert open_count_after_second == open_count_after_first

    for rule_code in AgentFinding.objects.filter(
        deposit=deposit, status=AgentFinding.Status.OPEN
    ).values_list("rule_code", flat=True).distinct():
        count = AgentFinding.objects.filter(
            deposit=deposit, rule_code=rule_code, status=AgentFinding.Status.OPEN
        ).count()
        assert count == 1


# ---------------------------------------------------------------------------
# Test e: Review run does not change deposit fields
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_review_does_not_change_deposit_fields():
    institution = Institution.objects.create(name="Inst", code="INST5")
    officer = User.objects.create_user(
        username="officer_e", password="pw", role=User.Roles.OFFICER
    )
    deposit = _make_deposit(institution, officer)

    before_status = deposit.status
    before_amount = deposit.amount
    before_issue = deposit.issue_date
    before_maturity = deposit.maturity_date

    run_review_for_deposit(deposit, triggered_by=officer)

    deposit.refresh_from_db()
    assert deposit.status == before_status
    assert deposit.amount == before_amount
    assert deposit.issue_date == before_issue
    assert deposit.maturity_date == before_maturity


# ---------------------------------------------------------------------------
# Test f: INSTITUTION user gets 403 on resolve POST, 404 on another institution's finding
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_institution_user_blocked():
    institution_a = Institution.objects.create(name="Inst A", code="INST6A")
    institution_b = Institution.objects.create(name="Inst B", code="INST6B")
    user_a = User.objects.create_user(
        username="inst_a", password="pw", role=User.Roles.INSTITUTION,
        institution=institution_a,
    )
    officer = User.objects.create_user(
        username="officer_f", password="pw", role=User.Roles.OFFICER
    )

    deposit_b = _make_deposit(institution_b, officer)
    run_review_for_deposit(deposit_b, triggered_by=officer)
    finding = deposit_b.agent_findings.first()

    client = Client()
    client.force_login(user_a)

    url = reverse("agent:agent_finding_resolve", args=[finding.pk])
    response = client.post(url, {"note": "test"})
    assert response.status_code == 403

    url_detail = reverse("agent:agent_finding_detail", args=[finding.pk])
    response = client.get(url_detail)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test g: apply_suggestion for R01 transitions and audit log; not-allowed raises DomainError
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_apply_suggestion_r01_transitions_and_audit_log():
    institution = Institution.objects.create(name="Inst", code="INST7")
    officer = User.objects.create_user(
        username="officer_g", password="pw", role=User.Roles.OFFICER
    )
    deposit = _make_deposit(institution, officer, status=Deposit.Status.UNDER_SCRUTINY)

    review_run = run_review_for_deposit(deposit, triggered_by=officer)
    finding = AgentFinding.objects.create(
        review_run=review_run,
        deposit=deposit,
        severity="CRITICAL",
        category=AgentFinding.Category.MISMATCH,
        message="Amount mismatch test",
        rule_code="R01",
        status=AgentFinding.Status.OPEN,
    )

    before_status = deposit.status
    apply_suggestion(finding, officer)
    deposit.refresh_from_db()
    assert deposit.status == Deposit.Status.DISCREPANCY
    assert deposit.status != before_status

    audit = AuditLog.objects.filter(
        action="AGENT_SUGGESTION_APPLIED", model_name="Deposit", object_id=deposit.pk
    ).first()
    assert audit is not None
    assert audit.changes.get("rule_code") == "R01"

    finding.refresh_from_db()
    assert finding.status == AgentFinding.Status.OPEN


@pytest.mark.django_db
def test_apply_suggestion_not_allowed_raises_domain_error():
    institution = Institution.objects.create(name="Inst", code="INST8")
    officer = User.objects.create_user(
        username="officer_h", password="pw", role=User.Roles.OFFICER
    )
    deposit = _make_deposit(institution, officer, status=Deposit.Status.MATURED)

    review_run = run_review_for_deposit(deposit, triggered_by=officer)
    finding = AgentFinding.objects.create(
        review_run=review_run,
        deposit=deposit,
        severity="CRITICAL",
        category=AgentFinding.Category.MATURED,
        message="Matured not renewed",
        rule_code="R08",
        status=AgentFinding.Status.OPEN,
    )

    before_status = deposit.status
    with pytest.raises(DomainError):
        apply_suggestion(finding, officer)

    deposit.refresh_from_db()
    assert deposit.status == before_status
    assert AuditLog.objects.filter(
        action="AGENT_SUGGESTION_APPLIED", object_id=deposit.pk
    ).count() == 0