"""Audit log cryptographic hash chain verification."""

import hashlib
import json

from apps.audit.models import AuditLog


def verify_chain() -> dict:
    """Walk audit entries in ID order and verify cryptographic linkage and integrity.

    Returns:
        dict with keys:
            ok (bool): True if all hashed entries are intact and linked.
            checked (int): count of validated hashed entries.
            legacy_skipped (int): count of unhashed legacy entries before the chain.
            broken_at_id (int or None): ID of the first broken entry, or None if valid.
            reason (str): human-readable explanation of result.
    """
    checked = 0
    legacy_skipped = 0
    hashed_started = False
    expected_prev = ""

    for entry in AuditLog.objects.all().order_by("id"):
        # Legacy entry check
        if not entry.entry_hash:
            if hashed_started:
                return {
                    "ok": False,
                    "checked": checked,
                    "legacy_skipped": legacy_skipped,
                    "broken_at_id": entry.id,
                    "reason": f"Entry #{entry.id} is unhashed after hash chain has already started.",
                }
            legacy_skipped += 1
            continue

        hashed_started = True

        # Check prev_hash linkage
        if entry.prev_hash != expected_prev:
            return {
                "ok": False,
                "checked": checked,
                "legacy_skipped": legacy_skipped,
                "broken_at_id": entry.id,
                "reason": (
                    f"Entry #{entry.id} prev_hash mismatch: expected '{expected_prev}', "
                    f"got '{entry.prev_hash}'."
                ),
            }

        # Recompute entry_hash
        payload_data = {
            "prev": entry.prev_hash,
            "actor_id": entry.actor_id,
            "action": entry.action,
            "model_name": entry.model_name,
            "object_id": entry.object_id,
            "changes": entry.changes if entry.changes is not None else {},
            "timestamp": entry.timestamp.isoformat(),
        }
        payload_bytes = json.dumps(payload_data, sort_keys=True, default=str).encode("utf-8")
        computed_hash = hashlib.sha256(payload_bytes).hexdigest()

        if computed_hash != entry.entry_hash:
            return {
                "ok": False,
                "checked": checked,
                "legacy_skipped": legacy_skipped,
                "broken_at_id": entry.id,
                "reason": (
                    f"Entry #{entry.id} hash mismatch: computed '{computed_hash}', "
                    f"stored '{entry.entry_hash}'."
                ),
            }

        checked += 1
        expected_prev = entry.entry_hash

    return {
        "ok": True,
        "checked": checked,
        "legacy_skipped": legacy_skipped,
        "broken_at_id": None,
        "reason": "Audit log hash chain is valid.",
    }
