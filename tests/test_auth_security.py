"""Tests for authentication security: rate limiting and password change."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.ratelimit import is_locked, rate_key

User = get_user_model()


class AuthSecurityTests(TestCase):
    """Test suite covering rate limiting, enumeration prevention, and password change."""

    def setUp(self):
        cache.clear()
        self.username = "cit_user"
        self.password = "CorrectPassword@123"
        self.user = User.objects.create_user(
            username=self.username,
            email="cit_user@example.com",
            password=self.password,
            role=User.Roles.INSTITUTION,
        )

    def tearDown(self):
        cache.clear()

    @override_settings(LOGIN_RATE_LIMIT_ATTEMPTS=5, LOGIN_RATE_LIMIT_LOCK_SECONDS=900)
    def test_five_wrong_passwords_lock_account_and_block_sixth_correct_attempt(self):
        """a. Five wrong passwords lock the account; 6th attempt with correct password shows lock error."""
        # 5 wrong attempts
        for _ in range(5):
            response = self.client.post(
                reverse("login"),
                {"username": self.username, "password": "WrongPassword@999"},
            )
            self.assertEqual(response.status_code, 200)

        # 6th attempt with the correct password
        response = self.client.post(
            reverse("login"),
            {"username": self.username, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Too many failed attempts. Try again in a few minutes."
        )
        # Verify the user is NOT logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_successful_login_clears_failure_counter(self):
        """b. A successful login clears the failure counter after 3 wrong attempts."""
        # 3 wrong attempts
        for _ in range(3):
            self.client.post(
                reverse("login"),
                {"username": self.username, "password": "WrongPassword@999"},
            )

        # Correct password succeeds
        response = self.client.post(
            reverse("login"),
            {"username": self.username, "password": self.password},
        )
        self.assertEqual(response.status_code, 302)

        # Counter should be cleared
        ip = "127.0.0.1"
        self.assertIsNone(cache.get(rate_key(self.username, ip)))
        self.assertFalse(is_locked(self.username, ip))

    def test_unknown_username_and_wrong_password_return_same_error_text(self):
        """c. Unknown username and wrong password return the same error text (no user enumeration)."""
        resp_wrong_pw = self.client.post(
            reverse("login"),
            {"username": self.username, "password": "WrongPassword@999"},
        )
        resp_unknown_user = self.client.post(
            reverse("login"),
            {"username": "unknown_user_12345", "password": "WrongPassword@999"},
        )

        form_wrong_pw = resp_wrong_pw.context["form"]
        form_unknown_user = resp_unknown_user.context["form"]

        self.assertEqual(
            form_wrong_pw.non_field_errors(),
            form_unknown_user.non_field_errors(),
        )

    def test_cache_key_does_not_contain_raw_username_or_ip(self):
        """d. The cache key does not contain the raw username or IP."""
        key = rate_key("cit_user", "192.168.1.100")
        self.assertNotIn("cit_user", key)
        self.assertNotIn("192.168.1.100", key)
        self.assertTrue(key.startswith("login-fail:"))

    def test_password_change_get_access_control(self):
        """e. GET /accounts/password/change/ returns 200 for logged-in user and redirects anonymous."""
        # Anonymous user gets redirected to login
        anon_response = self.client.get(reverse("password_change"))
        self.assertEqual(anon_response.status_code, 302)
        self.assertIn(reverse("login"), anon_response.url)

        # Logged-in user gets 200
        self.client.force_login(self.user)
        auth_response = self.client.get(reverse("password_change"))
        self.assertEqual(auth_response.status_code, 200)
        self.assertTemplateUsed(auth_response, "accounts/password_change.html")

    def test_password_change_post_success_and_failure(self):
        """f. POST with correct old password changes it; POST with wrong old password fails."""
        self.client.force_login(self.user)
        new_password = "NewSecurePassword@456"

        # POST with correct old password and valid new password
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": self.password,
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("password_change_done"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        # POST with wrong old password fails
        response_fail = self.client.post(
            reverse("password_change"),
            {
                "old_password": "IncorrectOldPassword@000",
                "new_password1": "AnotherNewPassword@789",
                "new_password2": "AnotherNewPassword@789",
            },
        )
        self.assertEqual(response_fail.status_code, 200)

        # Password remains the previously set one
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password("AnotherNewPassword@789"))
