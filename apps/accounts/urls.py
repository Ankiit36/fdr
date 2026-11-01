"""URLs for the accounts app."""

from django.urls import path

from apps.accounts.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
    path(
        "password/change/done/",
        PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
]
