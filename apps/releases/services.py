"""Domain services for release requests and lifecycle transitions."""

from django.db import transaction
from django.http import Http404
from django.utils import timezone

from apps.accounts.permissions import is_admin, is_institution_user, is_officer
from apps.audit.services import write_audit_log
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError
from apps.releases.eligibility import evaluate_release_eligibility
from apps.releases.models import Release

ALLOWED_TRANSITIONS = {
    Release.Status.REQUESTED: (Release.Status.UNDER_REVIEW, Release.Status.REJECTED),
    Release.Status.UNDER_REVIEW: (Release.Status.APPROVED, Release.Status.REJECTED),
    Release.Status.APPROVED: (Release.Status.PAID_OUT,),
    Release.Status.REJECTED: (),
    Release.Status.PAID_OUT: (),
}


def get_visible_releases(user, queryset=None):
    """Return releases visible to the user based on role and institution."""
    if queryset is None:
        queryset = Release.objects.all()

    if not user.is_authenticated:
        return queryset.none()

    if is_admin(user) or is_officer(user):
        return queryset

    if is_institution_user(user):
        if getattr(user, "institution_id", None):
            return queryset.filter(deposit__institution_id=user.institution_id)
        return queryset.none()

    return queryset.none()


def get_release_for_user(user, release_id):
    """Return a single release or raise Http404 if not visible to the user."""
    release = get_visible_releases(user).filter(pk=release_id).first()
    if release is None:
        raise Http404("Release not found.")
    return release


def get_release_list_queryset(user, status=None):
    """Return filtered release queryset visible to the user."""
    queryset = get_visible_releases(user)
    if status:
        queryset = queryset.filter(status=status)
    return queryset.order_by("-created_at")


def request_release(deposit, actor, request_type, note=""):
    """Request a release, discharge, or refund for a deposit."""
    if not (
        is_admin(actor)
        or (is_institution_user(actor) and actor.institution_id == deposit.institution_id)
    ):
        raise DomainError("Only institutions for this deposit or administrators may request a release.")

    active_exists = Release.objects.filter(
        deposit=deposit,
        status__in=[
            Release.Status.REQUESTED,
            Release.Status.UNDER_REVIEW,
            Release.Status.APPROVED,
        ],
    ).exists()
    if active_exists:
        raise DomainError("An active release request already exists for this deposit.")

    eligibility = evaluate_release_eligibility(deposit, request_type)
    if not eligibility.get("eligible"):
        failed_reasons = [c["reason"] for c in eligibility.get("checks", []) if not c.get("passed")]
        raise DomainError("; ".join(failed_reasons))

    with transaction.atomic():
        release = Release.objects.create(
            deposit=deposit,
            request_type=request_type,
            status=Release.Status.REQUESTED,
            amount=deposit.amount,
            requested_by=actor,
            decision_note=note or "",
            eligibility_result=eligibility,
            eligibility_checked_at=timezone.now(),
        )
        write_audit_log(
            actor=actor,
            action="RELEASE_REQUESTED",
            model_name="Release",
            object_id=release.pk,
            changes={
                "deposit_id": deposit.pk,
                "request_type": str(release.request_type),
                "amount": str(release.amount),
                "status": str(release.status),
                "note": note or "",
            },
        )
    return release


def start_review(release, actor):
    """Transition release from REQUESTED to UNDER_REVIEW (OFFICER or ADMIN)."""
    if not (is_officer(actor) or is_admin(actor)):
        raise DomainError("Only officers or administrators may start review.")

    if Release.Status.UNDER_REVIEW not in ALLOWED_TRANSITIONS.get(release.status, ()):
        raise DomainError(
            f"Invalid status transition for release #{release.pk}: "
            f"'{release.status}' -> '{Release.Status.UNDER_REVIEW}'."
        )

    with transaction.atomic():
        old_status = release.status
        release.status = Release.Status.UNDER_REVIEW
        release.save(update_fields=["status", "updated_at"])
        write_audit_log(
            actor=actor,
            action="RELEASE_UNDER_REVIEW",
            model_name="Release",
            object_id=release.pk,
            changes={"status": {"from": str(old_status), "to": str(release.status)}},
        )
    return release


def approve_release(release, actor, note):
    """Transition release from UNDER_REVIEW to APPROVED (OFFICER or ADMIN)."""
    if not (is_officer(actor) or is_admin(actor)):
        raise DomainError("Only officers or administrators may approve releases.")

    cleaned_note = (note or "").strip()
    if not cleaned_note:
        raise DomainError("A decision note is required to approve.")

    if Release.Status.APPROVED not in ALLOWED_TRANSITIONS.get(release.status, ()):
        raise DomainError(
            f"Invalid status transition for release #{release.pk}: "
            f"'{release.status}' -> '{Release.Status.APPROVED}'."
        )

    with transaction.atomic():
        old_status = release.status
        release.status = Release.Status.APPROVED
        release.reviewed_by = actor
        release.reviewed_at = timezone.now()
        release.decision_note = cleaned_note
        release.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "decision_note",
                "updated_at",
            ]
        )
        write_audit_log(
            actor=actor,
            action="RELEASE_APPROVED",
            model_name="Release",
            object_id=release.pk,
            changes={
                "status": {"from": str(old_status), "to": str(release.status)},
                "decision_note": cleaned_note,
            },
        )
    return release


def reject_release(release, actor, note):
    """Transition release from REQUESTED or UNDER_REVIEW to REJECTED (OFFICER or ADMIN)."""
    if not (is_officer(actor) or is_admin(actor)):
        raise DomainError("Only officers or administrators may reject releases.")

    cleaned_note = (note or "").strip()
    if not cleaned_note:
        raise DomainError("A decision note is required to reject.")

    if Release.Status.REJECTED not in ALLOWED_TRANSITIONS.get(release.status, ()):
        raise DomainError(
            f"Invalid status transition for release #{release.pk}: "
            f"'{release.status}' -> '{Release.Status.REJECTED}'."
        )

    with transaction.atomic():
        old_status = release.status
        release.status = Release.Status.REJECTED
        release.reviewed_by = actor
        release.reviewed_at = timezone.now()
        release.decision_note = cleaned_note
        release.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "decision_note",
                "updated_at",
            ]
        )
        write_audit_log(
            actor=actor,
            action="RELEASE_REJECTED",
            model_name="Release",
            object_id=release.pk,
            changes={
                "status": {"from": str(old_status), "to": str(release.status)},
                "decision_note": cleaned_note,
            },
        )
    return release


def mark_paid_out(release, actor):
    """Transition release from APPROVED to PAID_OUT (ADMIN only)."""
    if not is_admin(actor):
        raise DomainError("Only administrators may mark releases as paid out.")

    if Release.Status.PAID_OUT not in ALLOWED_TRANSITIONS.get(release.status, ()):
        raise DomainError(
            f"Invalid status transition for release #{release.pk}: "
            f"'{release.status}' -> '{Release.Status.PAID_OUT}'."
        )

    with transaction.atomic():
        old_status = release.status
        release.status = Release.Status.PAID_OUT
        release.save(update_fields=["status", "updated_at"])
        write_audit_log(
            actor=actor,
            action="RELEASE_PAID_OUT",
            model_name="Release",
            object_id=release.pk,
            changes={"status": {"from": str(old_status), "to": str(release.status)}},
        )
    return release
