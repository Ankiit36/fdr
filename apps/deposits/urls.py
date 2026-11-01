"""URL patterns for the deposits app."""

from django.urls import path

from apps.agent import views as agent_views
from apps.deposits import views

urlpatterns = [
    path("", views.DepositListView.as_view(), name="deposit_list"),
    path("export/csv/", views.DepositExportCSVView.as_view(), name="deposit_export_csv"),
    path("new/", views.DepositCreateView.as_view(), name="deposit_create"),
    path("<int:pk>/", views.DepositDetailView.as_view(), name="deposit_detail"),
    path("<int:pk>/timeline/", views.DepositTimelineView.as_view(), name="deposit_timeline"),
    path("<int:pk>/edit/", views.DepositUpdateView.as_view(), name="deposit_update"),
    path("<int:pk>/delete/", views.DepositDeleteView.as_view(), name="deposit_delete"),
    path("<int:pk>/scrutiny/add/", views.ScrutinyAddView.as_view(), name="deposit_scrutiny_add"),
    path("<int:pk>/status/", views.DepositStatusUpdateView.as_view(), name="deposit_status_update"),
    path("<int:pk>/renew/", views.DepositRenewalView.as_view(), name="deposit_renew"),
    path(
        "<int:pk>/review/",
        agent_views.DepositReviewView.as_view(),
        name="deposit_review",
    ),
]
