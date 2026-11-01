"""URL patterns for the agent app."""

from django.urls import path

from apps.agent import views

app_name = "agent"

urlpatterns = [
    path(
        "findings/",
        views.FindingListView.as_view(),
        name="agent_finding_list",
    ),
    path(
        "findings/<int:pk>/",
        views.FindingDetailView.as_view(),
        name="agent_finding_detail",
    ),
    path(
        "findings/<int:pk>/acknowledge/",
        views.FindingAcknowledgeView.as_view(),
        name="agent_finding_acknowledge",
    ),
    path(
        "findings/<int:pk>/resolve/",
        views.FindingResolveView.as_view(),
        name="agent_finding_resolve",
    ),
    path(
        "findings/<int:pk>/apply/",
        views.FindingApplyView.as_view(),
        name="agent_finding_apply",
    ),
]