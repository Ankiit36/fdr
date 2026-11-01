"""Small deposit CRUD service tests."""

import pytest
from django.http import Http404
from datetime import date
from decimal import Decimal

from apps.accounts.models import User
from apps.deposits.models import Deposit
from apps.deposits.services import DomainError, create_deposit, get_deposit_for_user
from apps.institutions.models import Institution


@pytest.mark.django_db
def test_institution_cannot_see_another_institutions_deposit():
    institution_a = Institution.objects.create(name="Institution A", code="INSTA1")
    institution_b = Institution.objects.create(name="Institution B", code="INSTB1")
    user_a = User.objects.create_user(
        username="inst_a",
        password="pw",
        role=User.Roles.INSTITUTION,
        institution=institution_a,
    )
    officer = User.objects.create_user(username="officer_crud", password="pw", role=User.Roles.OFFICER)

    deposit_b = Deposit.objects.create(
        institution=institution_b,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="REF-B",
        bank_name="Bank B",
        amount=Decimal("1000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        created_by=officer,
    )

    with pytest.raises(Http404):
        get_deposit_for_user(user_a, deposit_b.pk)


@pytest.mark.django_db
def test_institution_cannot_create_deposit_for_another_institution():
    institution_a = Institution.objects.create(name="Institution A", code="INSTA2")
    institution_b = Institution.objects.create(name="Institution B", code="INSTB2")
    user_a = User.objects.create_user(
        username="inst_a2",
        password="pw",
        role=User.Roles.INSTITUTION,
        institution=institution_a,
    )

    with pytest.raises(DomainError):
        create_deposit(
            institution=institution_b,
            instrument_type=Deposit.InstrumentType.FDR,
            reference_number="REF-C",
            bank_name="Bank C",
            amount=Decimal("1000.00"),
            issue_date=date(2026, 1, 1),
            maturity_date=date(2027, 1, 1),
            created_by=user_a,
        )


@pytest.mark.django_db
def test_maturity_before_issue_date_is_rejected():
    institution = Institution.objects.create(name="Institution C", code="INSTC1")
    user = User.objects.create_user(username="officer_crud2", password="pw", role=User.Roles.OFFICER)

    with pytest.raises(DomainError):
        create_deposit(
            institution=institution,
            instrument_type=Deposit.InstrumentType.FDR,
            reference_number="REF-D",
            bank_name="Bank D",
            amount=Decimal("1000.00"),
            issue_date=date(2027, 1, 1),
            maturity_date=date(2026, 1, 1),
            created_by=user,
        )


@pytest.mark.django_db
def test_future_issue_date_is_rejected():
    institution = Institution.objects.create(name="Institution Fut", code="INSTFUT")
    admin_user = User.objects.create_user(username="admin_fut", password="pw", role=User.Roles.ADMIN)
    with pytest.raises(DomainError) as exc_info:
        create_deposit(
            institution=institution,
            instrument_type=Deposit.InstrumentType.FDR,
            reference_number="REF-FUT",
            bank_name="Bank Fut",
            amount=Decimal("1000.00"),
            issue_date=date(2027, 1, 1),
            maturity_date=date(2028, 1, 1),
            created_by=admin_user,
        )
    assert "issue_date cannot be in the future" in str(exc_info.value)
