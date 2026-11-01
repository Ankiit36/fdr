"""DRF API tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.deposits.models import Deposit
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


# ---------------------------------------------------------------------------
# Test a: INSTITUTION user sees only own institution's deposits
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_institution_sees_only_own_deposits():
    institution_a = Institution.objects.create(name="Institution A", code="INSTA")
    institution_b = Institution.objects.create(name="Institution B", code="INSTB")
    user_a = _make_user(User.Roles.INSTITUTION, institution_a)

    Deposit.objects.create(
        institution=institution_a,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="REF-A-1",
        bank_name="Bank A",
        amount=Decimal("1000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        created_by=user_a,
    )
    Deposit.objects.create(
        institution=institution_b,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="REF-B-1",
        bank_name="Bank B",
        amount=Decimal("2000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        created_by=user_a,
    )

    client = Client()
    client.force_login(user_a)
    response = client.get("/api/deposits/")
    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 1
    for result in data["results"]:
        assert result["institution"] == institution_a.pk


# ---------------------------------------------------------------------------
# Test b: INSTITUTION user gets 404 for another institution's deposit
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_institution_cannot_see_another_institutions_deposit():
    institution_a = Institution.objects.create(name="Institution A", code="INSTA")
    institution_b = Institution.objects.create(name="Institution B", code="INSTB")
    user_a = _make_user(User.Roles.INSTITUTION, institution_a)

    deposit_b = Deposit.objects.create(
        institution=institution_b,
        instrument_type=Deposit.InstrumentType.FDR,
        reference_number="REF-B-2",
        bank_name="Bank B",
        amount=Decimal("2000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2027, 1, 1),
        created_by=user_a,
    )

    client = Client()
    client.force_login(user_a)
    response = client.get(f"/api/deposits/{deposit_b.pk}/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test c: GET /api/schema/ returns 200
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_api_schema_returns_200():
    client = Client()
    response = client.get("/api/schema/")
    assert response.status_code == 200