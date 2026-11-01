"""Lifecycle timeline aggregator for FDR deposits."""

from apps.audit.models import AuditLog


def deposit_timeline(deposit):
    """Return chronological lifecycle events for a deposit.

    Aggregates events from:
      1. AuditLog rows for the Deposit (model_name="Deposit", object_id=deposit.pk)
      2. AuditLog rows for this deposit's Release objects (model_name="Release")
      3. DepositDocument upload records (uploaded_at)
      4. ScrutinyObservation records (created_at)
      5. Notification records linked to this deposit (created_at)

    Each event is a dict: {"at": datetime, "source": str, "action": str, "actor": str}
    """
    events = []

    # 1. Deposit audit logs
    deposit_logs = AuditLog.objects.filter(
        model_name="Deposit",
        object_id=deposit.pk,
    ).select_related("actor")
    for log in deposit_logs:
        events.append({
            "at": log.timestamp,
            "source": "AuditLog",
            "action": log.action,
            "actor": log.actor.username if log.actor else "System",
        })

    # 2. Release audit logs
    release_ids = list(deposit.releases.values_list("pk", flat=True))
    if release_ids:
        release_logs = AuditLog.objects.filter(
            model_name="Release",
            object_id__in=release_ids,
        ).select_related("actor")
        for log in release_logs:
            events.append({
                "at": log.timestamp,
                "source": "AuditLog",
                "action": f"Release #{log.object_id}: {log.action}",
                "actor": log.actor.username if log.actor else "System",
            })

    # 3. Uploaded documents
    for doc in deposit.documents.select_related("uploaded_by").all():
        events.append({
            "at": doc.uploaded_at,
            "source": "Document",
            "action": f"Uploaded document ({doc.doc_type})",
            "actor": doc.uploaded_by.username if doc.uploaded_by else "Unknown",
        })

    # 4. Scrutiny observations
    for obs in deposit.scrutiny_observations.select_related("officer").all():
        note_snippet = obs.note[:60] + "..." if len(obs.note) > 60 else obs.note
        events.append({
            "at": obs.created_at,
            "source": "Scrutiny",
            "action": f"Observation: {note_snippet}",
            "actor": obs.officer.username if obs.officer else "Officer",
        })

    # 5. Notifications
    for notif in deposit.notifications.select_related("user").all():
        msg_snippet = notif.message[:60] + "..." if len(notif.message) > 60 else notif.message
        events.append({
            "at": notif.created_at,
            "source": "Notification",
            "action": f"Notice: {msg_snippet}",
            "actor": notif.user.username if notif.user else "System",
        })

    # Sort events by time
    events.sort(key=lambda item: item["at"])
    return events
