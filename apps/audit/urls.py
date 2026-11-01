"""URL patterns for the audit app."""

from django.urls import path

from apps.audit import views

app_name = "audit"

urlpatterns = [
    path("", views.AuditLogListView.as_view(), name="audit_log_list"),
    path("verify/", views.AuditChainVerifyView.as_view(), name="audit_chain_verify"),
]
