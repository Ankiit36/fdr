"""Human-in-the-loop actions for agent findings.

These functions are the service layer for acknowledge/resolve/apply actions.
They never change deposit amount or dates; apply_suggestion may change
deposit status through the existing change_status service.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from apps.audit.services import write_audit_log
from apps.agent.models import AgentFinding
from apps.deposits.services import DomainError, change_status

APPLY_MAP = {
    "R01": "DISCREPANCY",
    "R02": "DISCREPANCY",
    "R03": "DISCREPANCY",
    "R08": "MATURED",
}


def acknowledge_finding(finding, actor):
    """Transition an OPEN finding to ACKNOWLEDGED.

    Raises DomainError if the finding is not OPEN.
    """
    if finding.status != AgentFinding.Status.OPEN:
        raise DomainError(
            f"Finding {finding.pk} is not OPEN (status={finding.status}); "
            "only OPEN findings can be acknowledged."
        )
    finding.status = AgentFinding.Status.ACKNOWLEDGED
    finding.save(update_fields=["status"])
    return finding


def resolve_finding(finding, actor, note):
    """Transition an OPEN or ACKNOWLEDGED finding to RESOLVED.

    ``note`` is required (stripped; empty raises DomainError).
    Sets resolved_by, resolved_at, and resolution_note.
    """
    resolution_note = (note or "").strip()
    if not resolution_note:
        raise DomainError("A resolution note is required.")

    if finding.status not in (
        AgentFinding.Status.OPEN,
        AgentFinding.Status.ACKNOWLEDGED,
    ):
        raise DomainError(
            f"Finding {finding.pk} is not OPEN or ACKNOWLEDGED "
            f"(status={finding.status})."
        )

    finding.status = AgentFinding.Status.RESOLVED
    finding.resolved_by = actor
    finding.resolved_at = timezone.now()
    finding.resolution_note = resolution_note
    finding.save(
        update_fields=[
            "status",
            "resolved_by",
            "resolved_at",
            "resolution_note",
        ]
    )
    return finding


def apply_suggestion(finding, actor):
    """Apply the agent's suggestion to the deposit status.

    Looks up finding.rule_code in APPLY_MAP and calls change_status to move
    the deposit to the mapped status.  The transition is validated by
    change_status; if not allowed, DomainError is raised and nothing changes.

    Writes an AuditLog with action "AGENT_SUGGESTION_APPLIED".
    The finding is NOT auto-resolved.
    """
    rule_code = finding.rule_code
    if rule_code not in APPLY_MAP:
        raise DomainError(
            f"Rule code '{rule_code}' is not applicable via apply_suggestion."
        )

    new_status = APPLY_MAP[rule_code]
    deposit = finding.deposit
    old_status = deposit.status

    change_status(
        deposit,
        new_status,
        actor,
    )

    write_audit_log(
        actor=actor,
        action="AGENT_SUGGESTION_APPLIED",
        model_name="Deposit",
        object_id=deposit.pk,
        changes={
            "rule_code": rule_code,
            "from": str(old_status),
            "to": str(new_status),
        },
    )

    return deposit