"""Authentication views for the AICTE FDR Management Portal."""

from django.contrib.auth import views as auth_views

from apps.accounts.models import User


class LoginView(auth_views.LoginView):
    """Login view that redirects users to role based landing pages."""

    template_name = "accounts/login.html"

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
