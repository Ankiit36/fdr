"""Authentication views for the AICTE FDR Management Portal."""

from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from apps.accounts.models import User
from apps.accounts.ratelimit import (
    clear_failures,
    client_ip,
    is_locked,
    record_failure,
)


class LoginView(auth_views.LoginView):
    """Login view that redirects users to role based landing pages with rate limiting."""

    template_name = "accounts/login.html"

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "")
        ip = client_ip(request)

        if is_locked(username, ip):
            form = self.get_form()
            form.add_error(None, "Too many failed attempts. Try again in a few minutes.")
            return self.render_to_response(self.get_context_data(form=form))

        form = self.get_form()
        if form.is_valid():
            clear_failures(username, ip)
            return self.form_valid(form)
        else:
            record_failure(username, ip)
            return self.form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated:
            if user.role in (User.Roles.ADMIN, User.Roles.OFFICER):
                return "/dashboard/"
            if user.role == User.Roles.INSTITUTION:
                return "/deposits/"
        return "/accounts/login/?next=/accounts/login/"


class LogoutView(auth_views.LogoutView):
    """Logout view (POST only in Django 5)."""

    next_page = "/accounts/login/"


class PasswordChangeView(auth_views.PasswordChangeView):
    """Password change view using custom styled template."""

    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("password_change_done")


class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    """Confirmation view after password change."""

    template_name = "accounts/password_change_done.html"
