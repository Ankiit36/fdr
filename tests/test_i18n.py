"""Tests for Phase I18N: English and Hindi bilingual interface."""

import re

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.core.templatetags.i18n_hi import tr
from apps.core.translations import TRANSLATIONS


@pytest.fixture
def admin_user(db):
    """Create and return an admin user for testing."""
    return User.objects.create_user(
        username="admin_i18n",
        password="password123",
        role=User.Roles.ADMIN,
    )


# ---------------------------------------------------------------------------
# a. /lang/hi/ sets session, and GET /dashboard/ returns Devanagari characters
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_set_language_session_and_devanagari_dashboard(admin_user):
    client = Client()
    client.force_login(admin_user)

    switch_resp = client.get("/lang/hi/", follow=True)
    assert switch_resp.status_code == 200
    assert client.session.get("lang") == "hi"

    dash_resp = client.get("/dashboard/")
    assert dash_resp.status_code == 200
    content = dash_resp.content.decode("utf-8")
    assert re.search(r"[\u0900-\u097F]", content) is not None


# ---------------------------------------------------------------------------
# b. Same session shows English heading "Upcoming Maturities" when LANG is "en"
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_default_session_shows_english_upcoming_maturities(admin_user):
    client = Client()
    client.force_login(admin_user)

    # Explicitly set to 'en' or leave as default
    resp_en = client.get("/dashboard/")
    assert resp_en.status_code == 200
    content_en = resp_en.content.decode("utf-8")
    assert "Upcoming Maturities" in content_en


# ---------------------------------------------------------------------------
# c. Login page with lang hi contains Devanagari and does not contain English title text
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_login_page_with_lang_hi():
    client = Client()
    client.get("/lang/hi/", follow=True)

    resp = client.get("/accounts/login/")
    assert resp.status_code == 200
    content = resp.content.decode("utf-8")
    assert re.search(r"[\u0900-\u097F]", content) is not None
    assert "Sign in to manage deposits and FDRs" not in content


# ---------------------------------------------------------------------------
# d. Deposits list, releases list, agent findings list, audit list (ADMIN),
#    and notifications list each return 200 with lang hi and contain Devanagari
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_all_core_lists_return_devanagari_in_hindi(admin_user):
    client = Client()
    client.force_login(admin_user)
    client.get("/lang/hi/", follow=True)

    urls = [
        "/deposits/",
        "/releases/",
        "/agent/findings/",
        "/audit/",
        "/notifications/",
    ]
    for url in urls:
        resp = client.get(url)
        assert resp.status_code == 200, f"Expected 200 for {url}"
        content = resp.content.decode("utf-8")
        assert re.search(r"[\u0900-\u097F]", content) is not None, f"Expected Devanagari in {url}"


# ---------------------------------------------------------------------------
# e. tr() falls back to the key itself for an unknown key, and never raises
# ---------------------------------------------------------------------------
def test_tr_fallback_for_unknown_key():
    assert tr({}, "unknown.nonexistent.key") == "unknown.nonexistent.key"
    assert tr({"LANG": "hi"}, "another.unknown.key") == "another.unknown.key"
    assert tr({"LANG": "en"}, "foo.bar.baz") == "foo.bar.baz"
    assert tr(None, "no.context.key") == "no.context.key"


# ---------------------------------------------------------------------------
# f. Every key in TRANSLATIONS has non-empty 'en' and 'hi' values
# ---------------------------------------------------------------------------
def test_all_translations_keys_have_non_empty_values():
    assert len(TRANSLATIONS) > 0
    for key, entry in TRANSLATIONS.items():
        assert isinstance(entry, dict), f"Key {key} must have a dict value"
        assert "en" in entry, f"Key {key} is missing 'en'"
        assert isinstance(entry["en"], str) and entry["en"].strip(), f"Key {key} has empty 'en'"
        assert "hi" in entry, f"Key {key} is missing 'hi'"
        assert isinstance(entry["hi"], str) and entry["hi"].strip(), f"Key {key} has empty 'hi'"
