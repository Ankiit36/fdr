"""Document upload, download, verification and renewal tests."""

import pytest
from datetime import date
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError, renew_deposit
from apps.documents.models import DepositDocument
from apps.documents.services import DocumentValidationError, upload_document
from apps.institutions.models import Institution
from apps.verification.services import MockBankVerificationService, verify_deposit


def _make_deposit(institution, created_by, status=Deposit.Status.ACTIVE):
    return Deposit.objects.create(
        institution=institution,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number=f"REF-{institution.code}",
        bank_name=f"Bank {institution.code}",
        amount=Decimal("1000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        status=status,
        created_by=created_by,
    )


@pytest.mark.django_db
def test_institution_cannot_download_another_institutions_document(client):
    institution_a = Institution.objects.create(name="Institution A", code="INSTA9")
    institution_b = Institution.objects.create(name="Institution B", code="INSTB9")
    user_a = User.objects.create_user(
        username="inst_a9",
        password="pw",
        role=User.Roles.INSTITUTION,
        institution=institution_a,
    )
    officer = User.objects.create_user(username="officer_doc", password="pw", role=User.Roles.OFFICER)
    deposit_b = _make_deposit(institution_b, officer)
    document = DepositDocument.objects.create(
        deposit=deposit_b,
        doc_type="FDR_CERTIFICATE",
        file=SimpleUploadedFile("cert.pdf", b"%PDF-1234", content_type="application/pdf"),
        uploaded_by=officer,
    )

    client.force_login(user_a)
    response = client.get(f"/documents/{document.pk}/download/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_invalid_file_type_rejected():
    institution = Institution.objects.create(name="Institution C", code="INSTC9")
    officer = User.objects.create_user(username="officer_doc2", password="pw", role=User.Roles.OFFICER)
    deposit = _make_deposit(institution, officer)

    with pytest.raises(DocumentValidationError):
        upload_document(
            deposit,
            SimpleUploadedFile("notes.txt", b"hello world", content_type="text/plain"),
            "OTHER",
            officer,
        )


@pytest.mark.django_db
def test_empty_document_upload_rejected():
    institution = Institution.objects.create(name="Institution Empty", code="INSTEMP")
    officer = User.objects.create_user(username="officer_empty", password="pw", role=User.Roles.OFFICER)
    deposit = _make_deposit(institution, officer)

    with pytest.raises(DomainError):
        upload_document(
            deposit,
            SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf"),
            "OTHER",
            officer,
        )


@pytest.mark.django_db
def test_officer_verification_mock_confirmed_sets_bank_confirmed():
    institution = Institution.objects.create(name="Institution D", code="INSTD9")
    officer = User.objects.create_user(username="officer_doc3", password="pw", role=User.Roles.OFFICER)
    deposit = _make_deposit(institution, officer, status=Deposit.Status.UNDER_SCRUTINY)

    result = verify_deposit(
        deposit,
        officer,
        bank_verification_service=MockBankVerificationService(confirmed=True),
        outcome=Deposit.Status.VERIFIED,
    )

    assert deposit.verification_source == Deposit.VerificationSource.BANK_CONFIRMED
    assert deposit.status == Deposit.Status.VERIFIED
    assert result == Deposit.Status.VERIFIED


@pytest.mark.django_db
def test_renewal_marks_old_deposit_renewed():
    institution = Institution.objects.create(name="Institution E", code="INSTE9")
    admin_user = User.objects.create_user(username="admin_renew", password="pw", role=User.Roles.ADMIN)
    old = _make_deposit(institution, admin_user, status=Deposit.Status.ACTIVE)

    new_deposit = renew_deposit(
        previous_deposit=old,
        institution=institution,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="REF-NEW-1",
        bank_name="Bank Renewal",
        amount=Decimal("2000.00"),
        issue_date=date(2026, 6, 1),
        maturity_date=date(2027, 6, 1),
        created_by=admin_user,
    )

    old.refresh_from_db()
    assert old.status == Deposit.Status.RENEWED
    assert new_deposit.previous_deposit_id == old.pk
    assert AuditLog.objects.filter(
        model_name="Deposit",
        object_id=new_deposit.pk,
        action="RENEWAL_CREATED",
    ).exists()
