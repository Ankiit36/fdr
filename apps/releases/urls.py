"""URL configuration for the releases app."""

from django.urls import path
from apps.releases import views

app_name = "releases"

urlpatterns = [
    path("", views.ReleaseListView.as_view(), name="release_list"),
    path("export/csv/", views.ReleaseExportCSVView.as_view(), name="release_export_csv"),
    path("deposit/<int:pk>/request/", views.ReleaseRequestView.as_view(), name="release_request"),
    path("<int:pk>/", views.ReleaseDetailView.as_view(), name="release_detail"),
    path("<int:pk>/review/", views.ReleaseReviewView.as_view(), name="release_review"),
    path("<int:pk>/approve/", views.ReleaseApproveView.as_view(), name="release_approve"),
    path("<int:pk>/reject/", views.ReleaseRejectView.as_view(), name="release_reject"),
    path("<int:pk>/paid-out/", views.ReleasePaidOutView.as_view(), name="release_paid_out"),
]
