"""Eligibility engine for FDR release, discharge, and refund requests."""

from django.utils import timezone

from apps.agent.models import AgentFinding
from apps.deposits.models import Deposit
from apps.releases.models import Release


def evaluate_release_eligibility(deposit: Deposit, request_type: str) -> dict:
    """Evaluate release eligibility for a deposit across all standard rules.

    Returns a dict with 'eligible' (bool) and 'checks' (list of check dicts).
    Every check always runs so that all blocking reasons are surfaced together.
    """
    today = timezone.localdate()
    checks = []

    # E01 STATUS: deposit status is MATURED or ACTIVE
    e01_passed = deposit.status in (Deposit.Status.MATURED, Deposit.Status.ACTIVE)
    checks.append({
        "code": "E01",
        "passed": e01_passed,
        "reason": (
            f"Deposit status is {deposit.status}."
            if e01_passed
            else f"E01 STATUS: Deposit status must be ACTIVE or MATURED (currently '{deposit.status}')."
        ),
    })

    # E02 MATURITY_REACHED: maturity_date <= today for RELEASE and REFUND
    req_type_str = str(request_type).upper()
    if req_type_str == Release.RequestType.DISCHARGE:
        checks.append({
            "code": "E02",
            "passed": True,
            "reason": "not applicable for discharge",
        })
    else:
        e02_passed = deposit.maturity_date <= today
        checks.append({
            "code": "E02",
            "passed": e02_passed,
            "reason": (
                f"Maturity date {deposit.maturity_date} has been reached."
                if e02_passed
                else f"E02 MATURITY_REACHED: Maturity date {deposit.maturity_date} is in the future."
            ),
        })

    # E03 NO_OPEN_CRITICAL: no AgentFinding with severity CRITICAL and status OPEN
    critical_rule_codes = list(
        AgentFinding.objects.filter(
            deposit=deposit,
            severity=AgentFinding.Severity.CRITICAL,
            status=AgentFinding.Status.OPEN,
        ).values_list("rule_code", flat=True)
    )
    e03_passed = len(critical_rule_codes) == 0
    checks.append({
        "code": "E03",
        "passed": e03_passed,
        "reason": (
            "No open critical findings."
            if e03_passed
            else f"E03 NO_OPEN_CRITICAL: Open critical findings present: {', '.join(critical_rule_codes)}."
        ),
    })

    # E04 DOCUMENT_PRESENT: at least one DepositDocument exists for the deposit
    e04_passed = deposit.documents.exists()
    checks.append({
        "code": "E04",
        "passed": e04_passed,
        "reason": (
            "Deposit document is present."
            if e04_passed
            else "E04 DOCUMENT_PRESENT: No deposit document found."
        ),
    })

    # E05 VERIFIED_TIER: verification_tier is BANK_CONFIRMED, or status is VERIFIED
    tier = getattr(deposit, "verification_tier", Deposit.VerificationTier.SCANNED_MANUAL)
    e05_passed = (
        tier == Deposit.VerificationTier.BANK_CONFIRMED
        or deposit.status == Deposit.Status.VERIFIED
    )
    checks.append({
        "code": "E05",
        "passed": e05_passed,
        "reason": (
            f"Verification tier is {tier}."
            if e05_passed
            else f"E05 VERIFIED_TIER: Verification tier is {tier}."
        ),
    })

    # E06 LOCK_IN_ENDED: lock_in_end_date is null or <= today
    e06_passed = deposit.lock_in_end_date is None or deposit.lock_in_end_date <= today
    checks.append({
        "code": "E06",
        "passed": e06_passed,
        "reason": (
            "Lock-in period has ended or not specified."
            if e06_passed
            else f"E06 LOCK_IN_ENDED: Lock-in end date is {deposit.lock_in_end_date} (future date)."
        ),
    })

    eligible = all(c["passed"] for c in checks)
    return {
        "eligible": eligible,
        "checks": checks,
    }
