"""Service layer for institution management."""

from apps.institutions.models import Institution
from apps.audit.services import write_audit_log


def create_institution(
    *,
    actor,
    name,
    code,
    address="",
    contact_email="",
    contact_phone="",
    is_active=True,
) -> Institution:
    """Create a new institution."""
    institution = Institution.objects.create(
        name=name,
        code=code,
        address=address,
        contact_email=contact_email,
        contact_phone=contact_phone,
        is_active=is_active,
    )
    write_audit_log(
        actor=actor,
        action="INSTITUTION_CREATED",
        model_name="Institution",
        object_id=institution.pk,
        changes={"code": code, "name": name},
    )
    return institution


def update_institution(
    institution,
    *,
    actor,
    name=None,
    code=None,
    address=None,
    contact_email=None,
    contact_phone=None,
    is_active=None,
) -> Institution:
    """Update institution fields and write an audit entry."""
    changes = {}
    if name is not None and institution.name != name:
        institution.name = name
        changes["name"] = name
    if code is not None and institution.code != code:
        institution.code = code
        changes["code"] = code
    if address is not None and institution.address != address:
        institution.address = address
        changes["address"] = address
    if contact_email is not None and institution.contact_email != contact_email:
        institution.contact_email = contact_email
        changes["contact_email"] = contact_email
    if contact_phone is not None and institution.contact_phone != contact_phone:
        institution.contact_phone = contact_phone
        changes["contact_phone"] = contact_phone
    if is_active is not None and institution.is_active != is_active:
        institution.is_active = is_active
        changes["is_active"] = is_active
    institution.save()
    write_audit_log(
        actor=actor,
        action="INSTITUTION_UPDATED",
        model_name="Institution",
        object_id=institution.pk,
        changes=changes,
    )
    return institution


def deactivate_institution(institution, actor) -> Institution:
    """Deactivate an institution (never hard delete)."""
    institution.is_active = False
    institution.save()
    write_audit_log(
        actor=actor,
        action="INSTITUTION_DEACTIVATED",
        model_name="Institution",
        object_id=institution.pk,
        changes={"is_active": institution.is_active},
    )
    return institution
