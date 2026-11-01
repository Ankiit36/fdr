"""Agent service layer: review execution, case summary, and priority scoring.

The agent is read-only with respect to deposits: it never changes deposit
status, amount, or dates.  It only creates ReviewRun, ExtractedField, and
AgentFinding records.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from apps.agent.extraction import extract_from_file
from apps.agent.models import AgentFinding, ExtractedField, ReviewRun
from apps.agent.rules import RULE_FUNCTIONS

# Next action per highest severity (fixed mapping)
NEXT_ACTION_MAP = {
    "CRITICAL": "Officer should mark DISCREPANCY after manual check",
    "WARNING": "Officer should review and request clarification",
    "INFO": "Officer should note for next review cycle",
    "NONE": "No action required",
}

SEVERITY_ORDER = ("CRITICAL", "WARNING", "INFO")


def run_review_for_deposit(deposit, triggered_by=None):
    """Run a full agent review for a deposit.

    Creates a ReviewRun, extracts text/fields from every document of the
    deposit, saves ExtractedField rows, runs all rules, and creates
    AgentFinding rows.  Skips creating a finding when an OPEN finding with
    the same (deposit, rule_code) already exists.

    The deposit is never mutated.
    """
    review_run = ReviewRun.objects.create(deposit=deposit, triggered_by=triggered_by)

    # --- Extraction -------------------------------------------------------
    field_map: dict = {}  # field_name -> FieldExtraction (best one)
    for document in deposit.documents.all():
        file_path = document.file.path
        _text, fields = extract_from_file(file_path)
        for field in fields:
            ExtractedField.objects.create(
                review_run=review_run,
                deposit=deposit,
                document=document,
                field_name=field.field_name,
                extracted_value=field.extracted_value,
                source_snippet=field.source_snippet,
                extraction_status=field.extraction_status,
            )
            # Prefer OK status when multiple documents yield the same field
            existing = field_map.get(field.field_name)
            if existing is None or (
                field.extraction_status == "OK"
                and existing.extraction_status != "OK"
            ):
                field_map[field.field_name] = field

    # --- Rules ------------------------------------------------------------
    for rule_func in RULE_FUNCTIONS:
        result = rule_func(deposit, field_map)
        if not result.should_create:
            continue
        # Skip if an OPEN finding with the same (deposit, rule_code) exists
        if AgentFinding.objects.filter(
            deposit=deposit,
            rule_code=result.rule_code,
            status=AgentFinding.Status.OPEN,
        ).exists():
            continue
        AgentFinding.objects.create(
            review_run=review_run,
            deposit=deposit,
            severity=result.severity,
            category=result.category,
            message=result.message,
            rule_code=result.rule_code,
            params=getattr(result, "params", {}) or {},
        )

    # --- Forgery heuristics on PDF documents ------------------------------
    from apps.agent.forgery import check_pdf_structure

    for document in deposit.documents.all():
        if document.file and document.file.name.lower().endswith(".pdf"):
            try:
                forgery_results = check_pdf_structure(document.file.path)
                for item in forgery_results:
                    rule_code = item["rule_code"]
                    if AgentFinding.objects.filter(
                        deposit=deposit,
                        rule_code=rule_code,
                        status=AgentFinding.Status.OPEN,
                    ).exists():
                        continue
                    AgentFinding.objects.create(
                        review_run=review_run,
                        deposit=deposit,
                        severity=item["severity"],
                        category=item["category"],
                        message=item["message"],
                        rule_code=rule_code,
                        params=item.get("params", {}) or {},
                    )
            except Exception as exc:
                logger.warning("Could not execute forgery checks on %s: %s", document.file.name, exc)

    return review_run


def case_summary(deposit):
    """Return a case summary dict for a deposit.

    Keys:
      deposit            -- the Deposit instance
      status             -- current deposit status
      days_to_maturity   -- days from today to maturity_date (int, may be negative)
      open_findings      -- list of open AgentFinding rows
      findings_by_severity -- dict {CRITICAL: [...], WARNING: [...], INFO: [...]}
      next_action        -- fixed next-action string based on highest severity
    """
    today = timezone.localdate()
    days_to_maturity = (deposit.maturity_date - today).days

    open_findings = list(
        AgentFinding.objects.filter(
            deposit=deposit, status=AgentFinding.Status.OPEN
        ).order_by("-severity", "created_at")
    )

    findings_by_severity = {"CRITICAL": [], "WARNING": [], "INFO": []}
    for finding in open_findings:
        findings_by_severity[finding.severity].append(finding)

    # Determine next action from highest severity present
    next_action = NEXT_ACTION_MAP["NONE"]
    for sev in SEVERITY_ORDER:
        if findings_by_severity[sev]:
            next_action = NEXT_ACTION_MAP[sev]
            break

    return {
        "deposit": deposit,
        "status": deposit.status,
        "days_to_maturity": days_to_maturity,
        "open_findings": open_findings,
        "findings_by_severity": findings_by_severity,
        "next_action": next_action,
    }


def priority_score(finding):
    """Compute a priority score for an AgentFinding.

    Base: CRITICAL=3, WARNING=2, INFO=1.
    Bonus +1 when deposit amount > AGENT_HIGH_VALUE_AMOUNT.
    Bonus +1 when days left to maturity < REMINDER_WINDOW_DAYS.
    """
    base = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}.get(finding.severity, 0)
    score = base

    if finding.deposit.amount > settings.AGENT_HIGH_VALUE_AMOUNT:
        score += 1

    today = timezone.localdate()
    days_left = (finding.deposit.maturity_date - today).days
    if days_left < settings.REMINDER_WINDOW_DAYS:
        score += 1

    return score