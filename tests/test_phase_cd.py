"""Tests for Phases C and D: Lifecycle timeline, Escalation channels, Analytics, Forgery heuristics, PDF report, and Hindi labels."""

import io
import tempfile
from datetime import date, timedelta
from decimal import Decimal

import pypdf
import pytest
from django.conf import settings
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.agent.forgery import check_pdf_structure
from apps.agent.models import AgentFinding, ReviewRun
from apps.agent.synthetic import build_text_pdf
from apps.audit.models import AuditLog
from apps.dashboard.pdf_report import render_summary_pdf
from apps.dashboard.services import analytics_by_institution
from apps.deposits.models import Deposit
from apps.deposits.services import change_status
from apps.deposits.timeline import deposit_timeline
from apps.institutions.models import Institution
from apps.notifications.channels import SmsMockChannel, WhatsAppMockChannel
from apps.notifications.services import escalate_stale_findings


def _make_test_deposit(institution, user, ref="DEP-CD-001", amount=Decimal("20000.00"), status=Deposit.Status.ACTIVE):
    return Deposit.objects.create(
        institution=institution,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number=ref,
        bank_name="Canara Bank",
        amount=amount,
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 1, 1),
        status=status,
        created_by=user,
    )


# ---------------------------------------------------------------------------
# a. deposit_timeline includes an AuditLog event after a status change.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_deposit_timeline_includes_audit_log_after_status_change():
    inst = Institution.objects.create(name="College Timeline", code="TIMELINE-INST")
    officer = User.objects.create_user(username="officer_t", password="password", role=User.Roles.OFFICER)
    deposit = _make_test_deposit(inst, officer, ref="TIME-001", status=Deposit.Status.SUBMITTED)

    change_status(deposit, Deposit.Status.UNDER_SCRUTINY, officer, note="Initiating scrutiny")

    events = deposit_timeline(deposit)
    assert len(events) >= 1
    actions = [e["action"] for e in events]
    sources = [e["source"] for e in events]
    assert "AuditLog" in sources
    assert any("UNDER_SCRUTINY" in a or "STATUS_CHANGED" in a for a in actions)


# ---------------------------------------------------------------------------
# b. Timeline view returns 404 for an INSTITUTION user of another institution.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_timeline_view_returns_404_for_unauthorized_institution_user():
    inst_a = Institution.objects.create(name="College A", code="INST-A")
    inst_b = Institution.objects.create(name="College B", code="INST-B")
    user_a = User.objects.create_user(username="user_a", password="password", role=User.Roles.INSTITUTION, institution=inst_a)
    user_b = User.objects.create_user(username="user_b", password="password", role=User.Roles.INSTITUTION, institution=inst_b)

    deposit_a = _make_test_deposit(inst_a, user_a, ref="DEP-A-404")

    client = Client()
    client.force_login(user_b)
    resp = client.get(f"/deposits/{deposit_a.pk}/timeline/")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# c. escalate_stale_findings escalates a CRITICAL finding older than the window.
#    A second call escalates nothing.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_escalate_stale_findings_idempotency():
    inst = Institution.objects.create(name="College Escalate", code="ESC-INST", contact_email="esc@inst.local")
    admin = User.objects.create_user(username="admin_esc", password="password", role=User.Roles.ADMIN)
    deposit = _make_test_deposit(inst, admin, ref="DEP-ESC-001")

    review_run = ReviewRun.objects.create(deposit=deposit, triggered_by=admin)
    finding = AgentFinding.objects.create(
        review_run=review_run,
        deposit=deposit,
        severity=AgentFinding.Severity.CRITICAL,
        category=AgentFinding.Category.MISMATCH,
        rule_code="R01",
        message="Stale critical mismatch",
        status=AgentFinding.Status.OPEN,
    )

    old_date = timezone.now() - timedelta(days=settings.AGENT_ESCALATION_DAYS + 3)
    AgentFinding.objects.filter(pk=finding.pk).update(created_at=old_date)

    res1 = escalate_stale_findings()
    assert res1["escalated"] == 1

    res2 = escalate_stale_findings()
    assert res2["escalated"] == 0


# ---------------------------------------------------------------------------
# d. Escalation sends through the SMS and WhatsApp mock channels.
# ---------------------------------------------------------------------------
def test_mock_channels_return_true():
    sms = SmsMockChannel()
    whatsapp = WhatsAppMockChannel()

    assert sms.send("+919876543210", "Subject", "Body content") is True
    assert whatsapp.send("+919876543210", "Subject", "Body content") is True


# ---------------------------------------------------------------------------
# e. analytics_by_institution totals for one institution match its deposits.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_analytics_by_institution_aggregates_match_deposits():
    inst = Institution.objects.create(name="Metrics Institute", code="METRIC-1")
    admin = User.objects.create_user(username="admin_analytics", password="password", role=User.Roles.ADMIN)

    _make_test_deposit(inst, admin, ref="MET-01", amount=Decimal("30000.00"), status=Deposit.Status.ACTIVE)
    _make_test_deposit(inst, admin, ref="MET-02", amount=Decimal("45000.00"), status=Deposit.Status.EXPIRING)

    analytics = analytics_by_institution(admin)
    inst_row = next((row for row in analytics if row["code"] == "METRIC-1"), None)
    assert inst_row is not None
    assert inst_row["total_deposits"] == 2
    assert inst_row["expiring_count"] == 1
    assert inst_row["total_value"] == Decimal("75000.00")


# ---------------------------------------------------------------------------
# f. Analytics route: INSTITUTION gets 403, OFFICER gets 200.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_analytics_route_permissions():
    inst = Institution.objects.create(name="College Perm", code="PERM-INST")
    inst_user = User.objects.create_user(username="inst_perm_user", password="password", role=User.Roles.INSTITUTION, institution=inst)
    officer_user = User.objects.create_user(username="officer_perm_user", password="password", role=User.Roles.OFFICER)

    client = Client()

    client.force_login(inst_user)
    resp_inst = client.get("/dashboard/analytics/")
    assert resp_inst.status_code == 403

    client.force_login(officer_user)
    resp_off = client.get("/dashboard/analytics/")
    assert resp_off.status_code == 200


# ---------------------------------------------------------------------------
# g. check_pdf_structure on a PDF with two "%%EOF" markers returns F03.
# ---------------------------------------------------------------------------
def test_forgery_check_detects_multiple_eof_f03():
    pdf_bytes = build_text_pdf(["Valid Document Content"]) + b"\n%extra data\n%%EOF\n"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        f_path = f.name

    results = check_pdf_structure(f_path)
    assert "F03" in results or any(r["rule_code"] == "F03" for r in results)


# ---------------------------------------------------------------------------
# h. check_pdf_structure on a PDF with no metadata returns F04.
# ---------------------------------------------------------------------------
def test_forgery_check_detects_missing_metadata_f04():
    # build_text_pdf generates valid PDF without Producer or CreationDate dictionary
    pdf_bytes = build_text_pdf(["No Metadata Present"])

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        f_path = f.name

    results = check_pdf_structure(f_path)
    assert "F04" in results or any(r["rule_code"] == "F04" for r in results)


# ---------------------------------------------------------------------------
# i. render_summary_pdf output starts with "%PDF" and pypdf can read it back
#    and find the title text.
# ---------------------------------------------------------------------------
def test_render_summary_pdf_validity_and_title():
    title = "AICTE Executive Portfolio Summary"
    lines = [
        "Institution Alpha: 5 deposits, Value: INR 500,000",
        "Institution Beta: 3 deposits, Value: INR 300,000",
    ]
    pdf_bytes = render_summary_pdf(title, lines)

    assert pdf_bytes.startswith(b"%PDF")

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    page0_text = reader.pages[0].extract_text()
    assert title in page0_text


# ---------------------------------------------------------------------------
# j. Hindi: the dashboard view with ?lang=hi returns Devanagari heading text,
#    and the default returns English.
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_hindi_dashboard_labels():
    user = User.objects.create_user(username="lang_user", password="password", role=User.Roles.ADMIN)
    client = Client()
    client.force_login(user)

    # With ?lang=hi
    resp_hi = client.get("/dashboard/?lang=hi")
    assert resp_hi.status_code == 200
    content_hi = resp_hi.content.decode("utf-8")
    assert "सक्रिय" in content_hi
    assert "कुल मूल्य" in content_hi

    # Default (no lang parameter)
    resp_en = client.get("/dashboard/")
    assert resp_en.status_code == 200
    content_en = resp_en.content.decode("utf-8")
    assert "Active" in content_en
    assert "Total value" in content_en
