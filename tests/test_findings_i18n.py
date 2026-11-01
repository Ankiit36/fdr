"""Tests for Agent Findings Internationalization (Hindi/English structured messages)."""

from datetime import timedelta
from decimal import Decimal
import re

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.agent.messages_hi import render_finding_message
from apps.agent.models import AgentFinding, ReviewRun
from apps.agent.rules import MESSAGE_TEMPLATES
from apps.agent.services import run_review_for_deposit
from apps.deposits.models import Deposit
from apps.institutions.models import Institution


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="IIT Test", code="IIT-T1")


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin_findings_i18n",
        password="password123",
        role=User.Roles.ADMIN,
    )


# ---------------------------------------------------------------------------
# a. Creating an R08 finding through run_review_for_deposit stores params with
#    maturity_date and status.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_r08_finding_stores_params(institution, admin_user):
    past_date = timezone.localdate() - timedelta(days=30)
    deposit = Deposit.objects.create(
        institution=institution,
        reference_number="FDR-R08-PARAMS",
        bank_name="State Bank of India",
        amount=Decimal("100000.00"),
        issue_date=past_date - timedelta(days=365),
        maturity_date=past_date,
        status=Deposit.Status.ACTIVE,
        created_by=admin_user,
    )

    run_review_for_deposit(deposit, triggered_by=admin_user)

    finding = AgentFinding.objects.filter(deposit=deposit, rule_code="R08").first()
    assert finding is not None, "R08 finding should have been created"
    assert isinstance(finding.params, dict)
    assert "maturity_date" in finding.params
    assert "status" in finding.params
    assert finding.params["maturity_date"] == past_date.isoformat()
    assert finding.params["status"] == Deposit.Status.ACTIVE


# ---------------------------------------------------------------------------
# b. render_finding_message(finding, "hi") for that R08 finding contains
#    Devanagari characters (U+0900 to U+097F) and still contains the date
#    "2026-09-28" or the same date string from params.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_render_finding_message_hi(institution, admin_user):
    target_date_str = "2026-09-28"
    finding = AgentFinding(
        rule_code="R08",
        params={"maturity_date": target_date_str, "status": "MATURED"},
        message=f"Matured not renewed: maturity_date={target_date_str}, status=MATURED",
    )

    msg_hi = render_finding_message(finding, "hi")
    assert re.search(r"[\u0900-\u097F]", msg_hi) is not None, "Hindi message must contain Devanagari"
    assert target_date_str in msg_hi, f"Hindi message must preserve date string {target_date_str}"


# ---------------------------------------------------------------------------
# c. render_finding_message(finding, "en") equals the English template output,
#    and contains "Matured not renewed".
# ---------------------------------------------------------------------------
def test_render_finding_message_en():
    params = {"maturity_date": "2026-09-28", "status": "MATURED"}
    finding = AgentFinding(
        rule_code="R08",
        params=params,
        message="Matured not renewed: maturity_date=2026-09-28, status=MATURED",
    )

    msg_en = render_finding_message(finding, "en")
    expected_en = MESSAGE_TEMPLATES["R08"].format(**params)
    assert msg_en == expected_en
    assert "Matured not renewed" in msg_en


# ---------------------------------------------------------------------------
# d. A legacy finding with empty params returns finding.message unchanged for
#    both "hi" and "en".
# ---------------------------------------------------------------------------
def test_render_finding_message_legacy_empty_params():
    legacy_text = "Legacy R08 finding with unparsed message content"
    finding = AgentFinding(
        rule_code="R08",
        params={},
        message=legacy_text,
    )

    assert render_finding_message(finding, "hi") == legacy_text
    assert render_finding_message(finding, "en") == legacy_text
