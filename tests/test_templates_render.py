"""Smoke tests verifying that all templates render cleanly (status 200/403) for authorized roles."""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.institutions.models import Institution


@pytest.fixture
def auth_clients(db):
    inst = Institution.objects.create(name="Smoke Test Institution", code="SMOKE01")
    admin_user = User.objects.create_user(username="smoke_admin", password="pw", role=User.Roles.ADMIN)
    officer_user = User.objects.create_user(username="smoke_officer", password="pw", role=User.Roles.OFFICER)
    inst_user = User.objects.create_user(
        username="smoke_inst", password="pw", role=User.Roles.INSTITUTION, institution=inst
    )

    admin_client = Client()
    admin_client.force_login(admin_user)

    officer_client = Client()
    officer_client.force_login(officer_user)

    inst_client = Client()
    inst_client.force_login(inst_user)

    return {
        "admin": admin_client,
        "officer": officer_client,
        "institution": inst_client,
    }


@pytest.mark.django_db
def test_dashboard_renders_for_all(auth_clients):
    for role, client in auth_clients.items():
        resp = client.get("/dashboard/")
        assert resp.status_code == 200, f"Dashboard failed for {role}"


@pytest.mark.django_db
def test_deposits_renders_for_allowed_roles(auth_clients):
    for role in ["admin", "officer", "institution"]:
        resp = auth_clients[role].get("/deposits/")
        assert resp.status_code == 200, f"Deposits list failed for {role}"


@pytest.mark.django_db
def test_institutions_renders_for_allowed_roles(auth_clients):
    # ADMIN is authorized to view institutions list
    resp_admin = auth_clients["admin"].get("/institutions/")
    assert resp_admin.status_code == 200

    # Check officer access
    resp_officer = auth_clients["officer"].get("/institutions/")
    assert resp_officer.status_code in (200, 403)


@pytest.mark.django_db
def test_agent_findings_renders_for_allowed_roles(auth_clients):
    for role in ["admin", "officer", "institution"]:
        resp = auth_clients[role].get("/agent/findings/")
        assert resp.status_code == 200, f"Findings failed for {role}"


@pytest.mark.django_db
def test_releases_renders_for_all(auth_clients):
    for role, client in auth_clients.items():
        resp = client.get("/releases/")
        assert resp.status_code == 200, f"Releases failed for {role}"


@pytest.mark.django_db
def test_notifications_renders_for_all(auth_clients):
    for role, client in auth_clients.items():
        resp = client.get("/notifications/")
        assert resp.status_code == 200, f"Notifications failed for {role}"


@pytest.mark.django_db
def test_audit_permissions_and_render(auth_clients):
    # ADMIN: status 200
    resp_admin = auth_clients["admin"].get("/audit/")
    assert resp_admin.status_code == 200

    # INSTITUTION: status 403
    resp_inst = auth_clients["institution"].get("/audit/")
    assert resp_inst.status_code == 403
