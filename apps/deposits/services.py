"""Domain services for deposit creation, status transitions and renewals."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.permissions import is_admin, is_officer
from apps.audit.services import write_audit_log
from apps.deposits.models import Deposit, ScrutinyObservation


class DomainError(Exception):
    """Raised when a deposit domain business rule is violated."""


# Single source of truth for allowed deposit status transitions.
STATUS_TRANSITIONS = {
    Deposit.Status.SUBMITTED: (Deposit.Status.UNDER_SCRUTINY,),
    Deposit.Status.UNDER_SCRUTINY: (Deposit.Status.VERIFIED, Deposit.Status.DISCREPANCY),
    Deposit.Status.VERIFIED: (Deposit.Status.ACTIVE,),
    Deposit.Status.DISCREPANCY: (Deposit.Status.UNDER_SCRUTINY,),
    Deposit.Status.ACTIVE: (Deposit.Status.EXPIRING, Deposit.Status.RENEWED),
    Deposit.Status.EXPIRING: (Deposit.Status.MATURED, Deposit.Status.RENEWED),
    Deposit.Status.MATURED: (Deposit.Status.RENEWED,),
    Deposit.Status.RENEWED: (),
}


def get_allowed_status_transitions(status):
    """Return the tuple of statuses a deposit may transition into."""
    return STATUS_TRANSITIONS.get(status, ())


def change_status(deposit, new_status, actor, note=None, audit_action=None):
    """Transition a deposit to a new status (validated) and audit the change."""
    current_status = deposit.status
    allowed_transitions = get_allowed_status_transitions(current_status)

    if new_status not in allowed_transitions:
        raise DomainError(
            f"Invalid status transition for deposit '{deposit.reference_number}': "
            f"'{current_status}' -> '{new_status}'. "
            f"Allowed transitions: "
            f"{', '.join(str(status) for status in allowed_transitions) if allowed_transitions else 'none'}."
        )

    changes = {
        "status": {
            "from": str(current_status),
            "to": str(new_status),
        },
    }
    if note:
        changes["note"] = note

    deposit.status = new_status
    deposit.updated_at = timezone.now()
    deposit.save(update_fields=["status", "updated_at"])

    write_audit_log(
        actor=actor,
        action=audit_action or "STATUS_CHANGED",
        model_name="Deposit",
        object_id=deposit.pk,
        changes=changes,
    )
    return deposit


def get_reminder_window_days():
    """Return the number of days before maturity that reminders trigger."""
    return int(settings.REMINDER_WINDOW_DAYS)


def get_maturity_status(deposit, today=None):
    """Return EXPIRING / MATURED for a deposit based on its maturity date."""
    today = today or timezone.localdate()
    reminder_window_days = get_reminder_window_days()

    if deposit.status == Deposit.Status.RENEWED:
        return Deposit.Status.RENEWED

    if deposit.maturity_date < today:
        return Deposit.Status.MATURED

    if deposit.maturity_date <= today + timedelta(days=reminder_window_days):
        return Deposit.Status.EXPIRING

    return deposit.status


def validate_deposit(
    *,
    institution,
    reference_number,
    bank_name,
    amount,
    issue_date,
    maturity_date,
    exclude_deposit=None,
):
    """Validate deposit business rules (maturity after issue date, unique bank + reference)."""
    if not reference_number or not str(reference_number).strip():
        raise DomainError("Reference number is required.")
    if not bank_name or not str(bank_name).strip():
        raise DomainError("Bank name is required.")
    if amount is None or amount == "":
        raise DomainError("Amount is required.")
    if issue_date is None:
        raise DomainError("Issue date is required.")
    if maturity_date is None:
        raise DomainError("Maturity date is required.")

    if maturity_date <= issue_date:
        raise DomainError(
            f"Invalid deposit '{reference_number}': maturity_date must be after issue_date."
        )

    if issue_date > timezone.localdate():
        raise DomainError(
            f"Invalid deposit '{reference_number}': issue_date cannot be in the future."
        )

    duplicate_query = Deposit.objects.filter(bank_name=bank_name, reference_number=reference_number)
    if exclude_deposit is not None and exclude_deposit.pk is not None:
        duplicate_query = duplicate_query.exclude(pk=exclude_deposit.pk)
    if duplicate_query.exists():
        raise DomainError(
            f"Duplicate deposit: bank '{bank_name}' with reference number '{reference_number}' already exists."
        )


def create_deposit(
    *,
    institution,
    instrument_type,
    reference_number,
    bank_name,
    bank_branch="",
    amount,
    issue_date,
    maturity_date,
    lock_in_end_date=None,
    verification_tier=None,
    created_by,
    previous_deposit=None,
) -> Deposit:
    """Create a new deposit, enforcing business rules."""
    validate_deposit(
        institution=institution,
        reference_number=reference_number,
        bank_name=bank_name,
        amount=amount,
        issue_date=issue_date,
        maturity_date=maturity_date,
    )

    if created_by is not None and created_by.is_authenticated:
        if created_by.role == User.Roles.OFFICER:
            raise DomainError("Officers cannot create deposits.")
        if (
            created_by.role == User.Roles.INSTITUTION
            and (institution is None or institution.id != created_by.institution_id)
        ):
            raise DomainError("Institutions can only create deposits for their own institution.")

    with transaction.atomic():
        deposit = Deposit.objects.create(
            institution=institution,
            instrument_type=instrument_type,
            reference_number=reference_number,
            bank_name=bank_name,
            bank_branch=bank_branch,
            amount=amount,
            issue_date=issue_date,
            maturity_date=maturity_date,
            lock_in_end_date=lock_in_end_date,
            verification_tier=verification_tier or Deposit.VerificationTier.SCANNED_MANUAL,
            status=Deposit.Status.SUBMITTED,
            verification_source=Deposit.VerificationSource.INSTITUTION_SUBMITTED,
            previous_deposit=previous_deposit,
            created_by=created_by,
        )

        if previous_deposit is not None:
            change_status(
                previous_deposit,
                Deposit.Status.RENEWED,
                created_by,
                note="Renewal",
            )

        write_audit_log(
            actor=created_by,
            action="DEPOSIT_CREATED",
            model_name="Deposit",
            object_id=deposit.pk,
            changes={
                "institution": str(deposit.institution_id),
                "instrument_type": deposit.instrument_type,
                "bank_name": deposit.bank_name,
                "reference_number": deposit.reference_number,
                "amount": str(deposit.amount),
            },
        )

    check_cross_institution_duplicate(deposit, actor=created_by)
    return deposit


def get_visible_deposits(user, queryset=None):
    """Return the deposits visible to the given user.

    INSTITUTION users only see deposits of their own institution; users
    without an institution get an empty queryset. ADMIN and OFFICER users
    see all deposits.
    """
    queryset = Deposit.objects.all() if queryset is None else queryset
    if not user.is_authenticated:
        return queryset.none()
    if user.role == User.Roles.INSTITUTION:
        if user.institution_id:
            return queryset.filter(institution=user.institution)
        return queryset.none()
    return queryset


def get_deposit_for_user(user, deposit_id):
    """Return a deposit visible to the user or raise Http404.

    Objects belonging to another institution are treated as not found so
    that their existence is not leaked.
    """
    deposit = get_visible_deposits(user).filter(pk=deposit_id).first()
    if deposit is None:
        raise Http404("Deposit not found.")
    return deposit


def get_deposit_list_queryset(
    user,
    search=None,
    status=None,
    institution_id=None,
    issue_date_from=None,
    issue_date_to=None,
):
    """Return deposits visible to the user with search and filters applied."""
    queryset = get_visible_deposits(user)
    if search:
        queryset = queryset.filter(
            Q(reference_number__icontains=search) | Q(bank_name__icontains=search)
        )
    if status:
        queryset = queryset.filter(status=status)
    if institution_id and (is_admin(user) or is_officer(user)):
        queryset = queryset.filter(institution_id=institution_id)
    if issue_date_from:
        queryset = queryset.filter(issue_date__gte=issue_date_from)
    if issue_date_to:
        queryset = queryset.filter(issue_date__lte=issue_date_to)
    return queryset.order_by("-created_at")


def check_cross_institution_duplicate(deposit, actor=None):
    """Check for cross-institution duplicate suspect (same ref + amount, different bank).

    If found, create an AgentFinding with rule_code 'R11_CROSS_INSTITUTION_DUPLICATE'.
    Respects the open finding constraint so findings are not duplicated.
    """
    from apps.agent.models import AgentFinding, ReviewRun
    from apps.agent.rules import MESSAGE_TEMPLATES

    candidates = (
        Deposit.objects.exclude(institution=deposit.institution)
        .filter(reference_number=deposit.reference_number, amount=deposit.amount)
        .exclude(pk=deposit.pk)
    )

    dep_bank_clean = deposit.bank_name.strip().lower()

    for other in candidates:
        if other.bank_name.strip().lower() != dep_bank_clean:
            # Check if deposit already has an OPEN finding for R11_CROSS_INSTITUTION_DUPLICATE
            has_open = AgentFinding.objects.filter(
                deposit=deposit,
                rule_code="R11_CROSS_INSTITUTION_DUPLICATE",
                status=AgentFinding.Status.OPEN,
            ).exists()

            # Also check if other deposit already has an OPEN finding pointing to this deposit
            has_reverse_open = AgentFinding.objects.filter(
                deposit=other,
                rule_code="R11_CROSS_INSTITUTION_DUPLICATE",
                status=AgentFinding.Status.OPEN,
                message__contains=f"conflicting_deposit={deposit.pk}",
            ).exists()

            if not has_open and not has_reverse_open:
                review_run = ReviewRun.objects.create(
                    deposit=deposit,
                    triggered_by=actor if (actor and actor.is_authenticated) else None,
                )
                template = MESSAGE_TEMPLATES.get(
                    "R11_CROSS_INSTITUTION_DUPLICATE",
                    "Duplicate suspect: reference={reference_number}, bank={bank_name}, conflicting_deposit={conflicting_pk}",
                )
                msg = template.format(
                    reference_number=deposit.reference_number,
                    bank_name=deposit.bank_name,
                    conflicting_pk=other.pk,
                )
                params = {
                    "reference_number": str(deposit.reference_number),
                    "bank_name": str(deposit.bank_name),
                    "conflicting_pk": str(other.pk),
                }
                AgentFinding.objects.create(
                    review_run=review_run,
                    deposit=deposit,
                    severity=AgentFinding.Severity.CRITICAL,
                    category=AgentFinding.Category.DUPLICATE_SUSPECT,
                    rule_code="R11_CROSS_INSTITUTION_DUPLICATE",
                    message=msg,
                    status=AgentFinding.Status.OPEN,
                    params=params,
                )
            break


def update_deposit(
    deposit,
    *,
    actor,
    institution=None,
    instrument_type=None,
    reference_number=None,
    bank_name=None,
    bank_branch=None,
    amount=None,
    issue_date=None,
    maturity_date=None,
    lock_in_end_date=None,
):
    """Update permitted deposit fields via the service layer and audit the change."""
    changes = {}
    if institution is not None and deposit.institution_id != institution.id:
        deposit.institution = institution
        changes["institution"] = institution.name
    if instrument_type is not None and deposit.instrument_type != instrument_type:
        deposit.instrument_type = instrument_type
        changes["instrument_type"] = instrument_type
    if reference_number is not None and deposit.reference_number != reference_number:
        deposit.reference_number = reference_number
        changes["reference_number"] = reference_number
    if bank_name is not None and deposit.bank_name != bank_name:
        deposit.bank_name = bank_name
        changes["bank_name"] = bank_name
    if bank_branch is not None and deposit.bank_branch != bank_branch:
        deposit.bank_branch = bank_branch
        changes["bank_branch"] = bank_branch
    if amount is not None and deposit.amount != amount:
        deposit.amount = amount
        changes["amount"] = str(amount)
    if issue_date is not None and deposit.issue_date != issue_date:
        deposit.issue_date = issue_date
        changes["issue_date"] = str(issue_date)
    if maturity_date is not None and deposit.maturity_date != maturity_date:
        deposit.maturity_date = maturity_date
        changes["maturity_date"] = str(maturity_date)
    if lock_in_end_date is not None and deposit.lock_in_end_date != lock_in_end_date:
        deposit.lock_in_end_date = lock_in_end_date
        changes["lock_in_end_date"] = str(lock_in_end_date)

    if changes:
        validate_deposit(
            institution=deposit.institution,
            reference_number=deposit.reference_number,
            bank_name=deposit.bank_name,
            amount=deposit.amount,
            issue_date=deposit.issue_date,
            maturity_date=deposit.maturity_date,
            exclude_deposit=deposit,
        )
        deposit.save()
        write_audit_log(
            actor=actor,
            action="DEPOSIT_UPDATED",
            model_name="Deposit",
            object_id=deposit.pk,
            changes=changes,
        )
        check_cross_institution_duplicate(deposit, actor=actor)

    return deposit


def delete_deposit(deposit, actor):
    """Write an audit entry and delete a deposit (ADMIN only)."""
    write_audit_log(
        actor=actor,
        action="DEPOSIT_DELETED",
        model_name="Deposit",
        object_id=deposit.pk,
        changes={
            "bank_name": deposit.bank_name,
            "reference_number": deposit.reference_number,
            "amount": str(deposit.amount),
        },
    )
    deposit.delete()


def add_scrutiny_observation(deposit, officer, note):
    """Record a scrutiny observation for a deposit."""
    observation = ScrutinyObservation.objects.create(
        deposit=deposit,
        officer=officer,
        note=note,
    )
    write_audit_log(
        actor=officer,
        action="SCRUTINY_OBSERVATION_ADDED",
        model_name="ScrutinyObservation",
        object_id=observation.pk,
        changes={"deposit": deposit.pk, "note": note},
    )
    return observation


def renew_deposit(
    *,
    previous_deposit,
    institution,
    instrument_type,
    reference_number,
    bank_name,
    bank_branch="",
    amount,
    issue_date,
    maturity_date,
    created_by,
) -> Deposit:
    """Start a renewal: create a new deposit linked to the previous one."""
    deposit = create_deposit(
        institution=institution,
        instrument_type=instrument_type,
        reference_number=reference_number,
        bank_name=bank_name,
        bank_branch=bank_branch,
        amount=amount,
        issue_date=issue_date,
        maturity_date=maturity_date,
        created_by=created_by,
        previous_deposit=previous_deposit,
    )
    write_audit_log(
        actor=created_by,
        action="RENEWAL_CREATED",
        model_name="Deposit",
        object_id=deposit.pk,
        changes={
            "previous_deposit": previous_deposit.pk,
            "reference_number": deposit.reference_number,
        },
    )
    return deposit
