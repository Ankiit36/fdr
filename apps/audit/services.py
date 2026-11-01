"""Audit service helpers."""

import hashlib
import json
from datetime import date

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog


def write_audit_log(actor, action, model_name, object_id, changes=None):
    """Write an immutable audit log entry into the cryptographic hash chain."""
    actor_id = actor.pk if (actor is not None and hasattr(actor, "pk")) else actor
    changes_dict = changes if changes is not None else {}

    with transaction.atomic():
        last_hashed = (
            AuditLog.objects.exclude(entry_hash="")
            .select_for_update()
            .order_by("-id")
            .first()
        )
        prev_hash = last_hashed.entry_hash if last_hashed else ""
        now = timezone.now()

        payload_data = {
            "prev": prev_hash,
            "actor_id": actor_id,
            "action": action,
            "model_name": model_name,
            "object_id": object_id,
            "changes": changes_dict,
            "timestamp": now.isoformat(),
        }
        payload_bytes = json.dumps(payload_data, sort_keys=True, default=str).encode("utf-8")
        entry_hash = hashlib.sha256(payload_bytes).hexdigest()

        return AuditLog.objects.create(
            actor=actor,
            action=action,
            model_name=model_name,
            object_id=object_id,
            changes=changes_dict,
            timestamp=now,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )


def filter_audit_logs(params):
    """Filter audit logs by user (username contains), model_name (exact), date_from, date_to.

    Invalid dates are ignored.
    """
    queryset = AuditLog.objects.all().order_by("-timestamp")

    user_query = params.get("user", "").strip()
    if user_query:
        queryset = queryset.filter(actor__username__icontains=user_query)

    model_query = params.get("model_name", "").strip()
    if model_query:
        queryset = queryset.filter(model_name=model_query)

    date_from_str = params.get("date_from", "").strip()
    if date_from_str:
        try:
            date_from = date.fromisoformat(date_from_str)
            queryset = queryset.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass

    date_to_str = params.get("date_to", "").strip()
    if date_to_str:
        try:
            date_to = date.fromisoformat(date_to_str)
            queryset = queryset.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass

    return queryset
