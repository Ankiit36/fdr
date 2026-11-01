"""Agent review rules for FDR deposits.

Each rule is a pure function returning a :class:`RuleResult`.  Rules never
mutate the deposit -- they only read deposit data and extracted field values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings

from apps.agent.extraction import STATUS_OK, STATUS_NO_TEXT_LAYER, FieldExtraction
from apps.agent.models import AgentFinding
from apps.deposits.models import Deposit
from apps.deposits.services import get_maturity_status


# ---------------------------------------------------------------------------
# Severity table (one dict, keyed by rule_code)
# ---------------------------------------------------------------------------
SEVERITY_TABLE = {
    "R01": "CRITICAL",
    "R02": "CRITICAL",
    "R03": "CRITICAL",
    "R04": "WARNING",
    "R05": "WARNING",
    "R06": "WARNING",
    "R07": "WARNING",
    "R08": "CRITICAL",
    "R09": "CRITICAL",
    "R10": "INFO",
    "R11": "CRITICAL",
    "R11_CROSS_INSTITUTION_DUPLICATE": "CRITICAL",
    "F01": "WARNING",
    "F02": "WARNING",
    "F03": "WARNING",
    "F04": "INFO",
}

# Category per rule_code
CATEGORY_TABLE = {
    "R01": AgentFinding.Category.MISMATCH,
    "R02": AgentFinding.Category.MISMATCH,
    "R03": AgentFinding.Category.MISMATCH,
    "R04": AgentFinding.Category.MISMATCH,
    "R05": AgentFinding.Category.NO_TEXT_LAYER,
    "R06": AgentFinding.Category.MISSING_DATA,
    "R07": AgentFinding.Category.MATURITY_SOON,
    "R08": AgentFinding.Category.MATURED,
    "R09": AgentFinding.Category.DUPLICATE_SUSPECT,
    "R10": AgentFinding.Category.RENEWAL_DUE,
    "R11": AgentFinding.Category.DUPLICATE_SUSPECT,
    "R11_CROSS_INSTITUTION_DUPLICATE": AgentFinding.Category.DUPLICATE_SUSPECT,
    "F01": AgentFinding.Category.FORGERY_SUSPECT,
    "F02": AgentFinding.Category.FORGERY_SUSPECT,
    "F03": AgentFinding.Category.FORGERY_SUSPECT,
    "F04": AgentFinding.Category.FORGERY_SUSPECT,
}

# Agent settings are read from django.conf.settings at call time inside each rule.


# ---------------------------------------------------------------------------
# Message templates per rule_code (no free-form text)
# ---------------------------------------------------------------------------
MESSAGE_TEMPLATES = {
    "R01": "Amount mismatch: submitted={submitted}, extracted={extracted}, snippet={snippet}",
    "R02": "Reference mismatch: submitted={submitted}, extracted={extracted}, snippet={snippet}",
    "R03": "Date mismatch: submitted={submitted}, extracted={extracted}, snippet={snippet}",
    "R04": "Bank mismatch: submitted={submitted}, extracted={extracted}, snippet={snippet}",
    "R05": "No text layer in document: {snippet}",
    "R06": "Missing document for deposit {reference_number}",
    "R07": "Maturity soon: maturity_date={maturity_date}, days_left={days_left}",
    "R08": "Matured not renewed: maturity_date={maturity_date}, status={status}",
    "R09": "Duplicate suspect: reference={reference_number}, bank={bank_name}, conflicting_deposit={conflicting_pk}",
    "R10": "Renewal due: maturity_date={maturity_date}, status=EXPIRING, days_left={days_left}",
    "R11": "Duplicate suspect: reference={reference_number}, bank={bank_name}, conflicting_deposit={conflicting_pk}",
    "R11_CROSS_INSTITUTION_DUPLICATE": "Duplicate suspect: reference={reference_number}, bank={bank_name}, conflicting_deposit={conflicting_pk}",
    "F01": "Editor or producer keyword detected in PDF metadata: {snippet} (metadata check, not proof)",
    "F02": "Modification date differs from creation date by more than 1 day (metadata check, not proof)",
    "F03": "Multiple %%EOF markers detected, indicating incremental update/append (metadata check, not proof)",
    "F04": "No Producer or CreationDate metadata found in PDF (metadata check, not proof)",
}


@dataclass(frozen=True)
class RuleResult:
    """Outcome of a single rule evaluation."""

    rule_code: str
    severity: str
    category: str
    message: str
    should_create: bool
    params: dict = field(default_factory=dict)


def _no_result(rule_code: str) -> RuleResult:
    """Return a RuleResult indicating the rule did not fire."""
    return RuleResult(
        rule_code=rule_code,
        severity=SEVERITY_TABLE[rule_code],
        category=CATEGORY_TABLE[rule_code],
        message="",
        should_create=False,
        params={},
    )


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------
def _parse_amount(value: str) -> Decimal | None:
    """Parse an extracted amount string (e.g. '5,00,000.00') into a Decimal."""
    try:
        return Decimal(re.sub(r"[^\d.]", "", value.strip()))
    except (InvalidOperation, ValueError):
        return None


def _parse_extracted_date(value: str):
    """Parse an extracted date string (DD/MM/YYYY, DD-MM-YYYY, DD Mon YYYY).

    Returns a ``datetime.date`` or ``None`` if it cannot be parsed.
    """
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalize_reference(value: str) -> str:
    """Normalize a reference number: strip whitespace, collapse internal spaces, uppercase."""
    return re.sub(r"\s+", "", value.strip()).upper()


def _get_field(field_map: dict, field_name: str) -> FieldExtraction | None:
    """Return the best extraction for a field (prefers OK status)."""
    return field_map.get(field_name)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def rule_amount_mismatch(deposit: Deposit, field_map: dict) -> RuleResult:
    """R01 AMOUNT_MISMATCH (CRITICAL).

    Compares deposit.amount with the extracted amount, allowing
    AGENT_AMOUNT_TOLERANCE difference.
    """
    field = _get_field(field_map, "amount")
    if not field or field.extraction_status != STATUS_OK:
        return _no_result("R01")
    extracted_amount = _parse_amount(field.extracted_value)
    if extracted_amount is None:
        return _no_result("R01")
    if abs(deposit.amount - extracted_amount) > settings.AGENT_AMOUNT_TOLERANCE:
        params = {
            "submitted": str(deposit.amount),
            "extracted": str(field.extracted_value),
            "snippet": str(field.source_snippet or ""),
        }
        return RuleResult(
            rule_code="R01",
            severity=SEVERITY_TABLE["R01"],
            category=CATEGORY_TABLE["R01"],
            message=MESSAGE_TEMPLATES["R01"].format(**params),
            should_create=True,
            params=params,
        )
    return _no_result("R01")


def rule_reference_mismatch(deposit: Deposit, field_map: dict) -> RuleResult:
    """R02 REFERENCE_MISMATCH (CRITICAL).

    Compares deposit.reference_number with the extracted reference number,
    normalizing spaces and case.
    """
    field = _get_field(field_map, "reference_number")
    if not field or field.extraction_status != STATUS_OK:
        return _no_result("R02")
    if _normalize_reference(deposit.reference_number) != _normalize_reference(
        field.extracted_value
    ):
        params = {
            "submitted": str(deposit.reference_number),
            "extracted": str(field.extracted_value),
            "snippet": str(field.source_snippet or ""),
        }
        return RuleResult(
            rule_code="R02",
            severity=SEVERITY_TABLE["R02"],
            category=CATEGORY_TABLE["R02"],
            message=MESSAGE_TEMPLATES["R02"].format(**params),
            should_create=True,
            params=params,
        )
    return _no_result("R02")


def rule_date_mismatch(deposit: Deposit, field_map: dict) -> RuleResult:
    """R03 DATE_MISMATCH (CRITICAL).

    Compares deposit.issue_date and deposit.maturity_date with the extracted
    dates.  Only DD/MM/YYYY, DD-MM-YYYY, DD Mon YYYY are recognised.
    """
    issues: list[str] = []
    submitted_parts: list[str] = []
    extracted_parts: list[str] = []
    snippets: list[str] = []

    for label, deposit_date, field_name in (
        ("issue_date", deposit.issue_date, "issue_date"),
        ("maturity_date", deposit.maturity_date, "maturity_date"),
    ):
        field = _get_field(field_map, field_name)
        if not field or field.extraction_status != STATUS_OK:
            continue
        extracted_date = _parse_extracted_date(field.extracted_value)
        if extracted_date is None:
            continue
        if extracted_date != deposit_date:
            issues.append(label)
            submitted_parts.append(str(deposit_date))
            extracted_parts.append(field.extracted_value)
            snippets.append(field.source_snippet)

    if issues:
        params = {
            "submitted": "; ".join(submitted_parts),
            "extracted": "; ".join(extracted_parts),
            "snippet": "; ".join(snippets),
        }
        return RuleResult(
            rule_code="R03",
            severity=SEVERITY_TABLE["R03"],
            category=CATEGORY_TABLE["R03"],
            message=MESSAGE_TEMPLATES["R03"].format(**params),
            should_create=True,
            params=params,
        )
    return _no_result("R03")


def rule_bank_mismatch(deposit: Deposit, field_map: dict) -> RuleResult:
    """R04 BANK_MISMATCH (WARNING).

    Case-insensitive ``contains`` check: the extracted bank name must be
    contained in the submitted bank name (or vice-versa).
    """
    field = _get_field(field_map, "bank_name")
    if not field or field.extraction_status != STATUS_OK:
        return _no_result("R04")
    submitted = deposit.bank_name.strip().lower()
    extracted = field.extracted_value.strip().lower()
    if submitted not in extracted and extracted not in submitted:
        params = {
            "submitted": str(deposit.bank_name),
            "extracted": str(field.extracted_value),
            "snippet": str(field.source_snippet or ""),
        }
        return RuleResult(
            rule_code="R04",
            severity=SEVERITY_TABLE["R04"],
            category=CATEGORY_TABLE["R04"],
            message=MESSAGE_TEMPLATES["R04"].format(**params),
            should_create=True,
            params=params,
        )
    return _no_result("R04")


def rule_no_text_layer(deposit: Deposit, field_map: dict) -> RuleResult:
    """R05 NO_TEXT_LAYER (WARNING).

    Fires when any extracted field reports NO_TEXT_LAYER (scanned PDF / image
    without OCR).
    """
    no_text_fields = [
        f for f in field_map.values() if f.extraction_status == STATUS_NO_TEXT_LAYER
    ]
    if no_text_fields:
        snippet = "; ".join(f.source_snippet or f.field_name for f in no_text_fields)
        params = {"snippet": str(snippet)}
        return RuleResult(
            rule_code="R05",
            severity=SEVERITY_TABLE["R05"],
            category=CATEGORY_TABLE["R05"],
            message=MESSAGE_TEMPLATES["R05"].format(**params),
            should_create=True,
            params=params,
        )
    return _no_result("R05")


def rule_missing_document(deposit: Deposit, field_map: dict) -> RuleResult:
    """R06 MISSING_DOCUMENT (WARNING).

    Fires when the deposit has no associated documents.
    """
    if not deposit.documents.exists():
        params = {"reference_number": str(deposit.reference_number)}
        return RuleResult(
            rule_code="R06",
            severity=SEVERITY_TABLE["R06"],
            category=CATEGORY_TABLE["R06"],
            message=MESSAGE_TEMPLATES["R06"].format(**params),
            should_create=True,
            params=params,
        )
    return _no_result("R06")


def rule_maturity_soon(deposit: Deposit, field_map: dict) -> RuleResult:
    """R07 MATURITY_SOON (WARNING).

    Uses the Phase 2 maturity function (get_maturity_status) and
    REMINDER_WINDOW_DAYS. Fires when the deposit is EXPIRING (maturity within
    the reminder window, not yet matured).
    """
    maturity_status = get_maturity_status(deposit)
    if maturity_status == Deposit.Status.EXPIRING:
        from django.utils import timezone

        today = timezone.localdate()
        days_left = (deposit.maturity_date - today).days
        params = {
            "maturity_date": deposit.maturity_date.isoformat(),
            "days_left": str(days_left),
        }
        return RuleResult(
            rule_code="R07",
            severity=SEVERITY_TABLE["R07"],
            category=CATEGORY_TABLE["R07"],
            message=MESSAGE_TEMPLATES["R07"].format(
                maturity_date=deposit.maturity_date,
                days_left=days_left,
            ),
            should_create=True,
            params=params,
        )
    return _no_result("R07")


def rule_matured_not_renewed(deposit: Deposit, field_map: dict) -> RuleResult:
    """R08 MATURED_NOT_RENEWED (CRITICAL).

    Fires when the maturity date has passed and the deposit has not been
    renewed.
    """
    from django.utils import timezone

    today = timezone.localdate()
    if deposit.maturity_date < today and deposit.status != Deposit.Status.RENEWED:
        params = {
            "maturity_date": deposit.maturity_date.isoformat(),
            "status": str(deposit.status),
        }
        return RuleResult(
            rule_code="R08",
            severity=SEVERITY_TABLE["R08"],
            category=CATEGORY_TABLE["R08"],
            message=MESSAGE_TEMPLATES["R08"].format(
                maturity_date=deposit.maturity_date,
                status=deposit.status,
            ),
            should_create=True,
            params=params,
        )
    return _no_result("R08")


def rule_duplicate_suspect(deposit: Deposit, field_map: dict) -> RuleResult:
    """R09 DUPLICATE_SUSPECT (CRITICAL).

    Fires when another deposit exists with the same bank_name and
    reference_number.
    """
    conflicting = (
        Deposit.objects.filter(
            bank_name=deposit.bank_name,
            reference_number=deposit.reference_number,
        )
        .exclude(pk=deposit.pk)
        .first()
    )
    if conflicting:
        params = {
            "reference_number": str(deposit.reference_number),
            "bank_name": str(deposit.bank_name),
            "conflicting_pk": str(conflicting.pk),
        }
        return RuleResult(
            rule_code="R09",
            severity=SEVERITY_TABLE["R09"],
            category=CATEGORY_TABLE["R09"],
            message=MESSAGE_TEMPLATES["R09"].format(**params),
            should_create=True,
            params=params,
        )
    return _no_result("R09")


def rule_renewal_due(deposit: Deposit, field_map: dict) -> RuleResult:
    """R10 RENEWAL_DUE (INFO).

    Fires when the deposit is EXPIRING and no other deposit has
    previous_deposit pointing to this deposit (no renewal child).
    """
    from django.utils import timezone

    today = timezone.localdate()
    days_left = (deposit.maturity_date - today).days
    has_renewal_child = Deposit.objects.filter(
        previous_deposit=deposit
    ).exists()
    if deposit.status == Deposit.Status.EXPIRING and not has_renewal_child:
        params = {
            "maturity_date": deposit.maturity_date.isoformat(),
            "days_left": str(days_left),
        }
        return RuleResult(
            rule_code="R10",
            severity=SEVERITY_TABLE["R10"],
            category=CATEGORY_TABLE["R10"],
            message=MESSAGE_TEMPLATES["R10"].format(
                maturity_date=deposit.maturity_date,
                days_left=days_left,
            ),
            should_create=True,
            params=params,
        )
    return _no_result("R10")


# Ordered list of all rule functions
RULE_FUNCTIONS = (
    rule_amount_mismatch,
    rule_reference_mismatch,
    rule_date_mismatch,
    rule_bank_mismatch,
    rule_no_text_layer,
    rule_missing_document,
    rule_maturity_soon,
    rule_matured_not_renewed,
    rule_duplicate_suspect,
    rule_renewal_due,
)

# Mapping rule_code -> rule function
RULE_BY_CODE = {
    "R01": rule_amount_mismatch,
    "R02": rule_reference_mismatch,
    "R03": rule_date_mismatch,
    "R04": rule_bank_mismatch,
    "R05": rule_no_text_layer,
    "R06": rule_missing_document,
    "R07": rule_maturity_soon,
    "R08": rule_matured_not_renewed,
    "R09": rule_duplicate_suspect,
    "R10": rule_renewal_due,
}