"""URL patterns for the dashboard app."""

from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("analytics/", views.AnalyticsView.as_view(), name="analytics"),
    path("reports/summary.pdf", views.SummaryPdfView.as_view(), name="summary_pdf"),
]
