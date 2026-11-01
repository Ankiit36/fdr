"""Permission helper and scoping tests."""

import pytest
from django.contrib.auth.models import AnonymousUser
from datetime import date
from decimal import Decimal

from apps.accounts.models import User
from apps.accounts.permissions import is_admin, is_institution_user, is_officer
from apps.deposits.models import Deposit
from apps.deposits.services import get_visible_deposits
from apps.documents.services import get_visible_documents
from apps.institutions.models import Institution


def _make_user(role, institution=None):
    username = f"{role.lower()}_{institution.code if institution else 'none'}"
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role,
        institution=institution,
    )


def test_role_helpers():
    assert is_admin(User(role=User.Roles.ADMIN)) is True
    assert is_officer(User(role=User.Roles.OFFICER)) is True
    assert is_institution_user(User(role=User.Roles.INSTITUTION)) is True

    assert is_admin(User(role=User.Roles.OFFICER)) is False
    assert is_officer(User(role=User.Roles.ADMIN)) is False
    assert is_institution_user(User(role=User.Roles.ADMIN)) is False

    assert is_admin(AnonymousUser()) is False
    assert is_officer(AnonymousUser()) is False
    assert is_institution_user(AnonymousUser()) is False


@pytest.mark.django_db
def test_get_visible_deposits_admin_and_officer_see_all():
    admin_user = User.objects.create_user(username="admin_scope", password="pw", role=User.Roles.ADMIN)
    officer = User.objects.create_user(username="officer_scope", password="pw", role=User.Roles.OFFICER)
    assert get_visible_deposits(admin_user).count() == get_visible_deposits(officer).count()


@pytest.mark.django_db
def test_get_visible_deposits_scopes_institution_user():
    institution_a = Institution.objects.create(name="Institution A", code="INSTA1")
    institution_b = Institution.objects.create(name="Institution B", code="INSTB1")
    user_a = User.objects.create_user(
        username="inst_a",
        password="pw",
        role=User.Roles.INSTITUTION,
        institution=institution_a,
    )
    user_b = User.objects.create_user(
        username="inst_b",
        password="pw",
        role=User.Roles.INSTITUTION,
        institution=institution_b,
    )
    officer = User.objects.create_user(username="officer_scope2", password="pw", role=User.Roles.OFFICER)

    def make_deposit(institution, ref):
        return Deposit.objects.create(
            institution=institution,
            instrument_type=Deposit.InstrumentType.FDR,
            reference_number=ref,
            bank_name=f"Bank {ref}",
            amount=Decimal("1000.00"),
            issue_date=date(2026, 1, 1),
            maturity_date=date(2027, 1, 1),
            created_by=officer,
        )

    deposit_a = make_deposit(institution_a, "REF-A")
    deposit_b = make_deposit(institution_b, "REF-B")

    assert get_visible_deposits(user_a).count() == 1
    assert get_visible_deposits(user_a).first().pk == deposit_a.pk
    assert get_visible_deposits(user_b).count() == 1
    assert get_visible_deposits(user_b).first().pk == deposit_b.pk


@pytest.mark.django_db
def test_get_visible_deposits_empty_for_unassigned_institution_user():
    user = User.objects.create_user(username="inst_unassigned", password="pw", role=User.Roles.INSTITUTION)
    assert get_visible_deposits(user).count() == 0
    assert get_visible_documents(user).count() == 0
