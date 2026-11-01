"""URL configuration for the AICTE Security Deposit / FDR Management Portal."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.accounts.views import LoginView, LogoutView
from apps.core.views import set_language_view

urlpatterns = [
    path("", RedirectView.as_view(url="/accounts/login/", permanent=False)),
    path("lang/<str:code>/", set_language_view, name="set_language"),
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("institutions/", include("apps.institutions.urls")),
    path("deposits/", include("apps.deposits.urls")),
    path("documents/", include("apps.documents.urls")),
    path("agent/", include("apps.agent.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("audit/", include("apps.audit.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("releases/", include("apps.releases.urls")),
    path("api/", include("config.api_urls")),
]
