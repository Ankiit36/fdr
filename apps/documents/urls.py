"""URL patterns for the documents app."""

from django.urls import path

from apps.documents import views

urlpatterns = [
    path("<int:pk>/download/", views.DocumentDownloadView.as_view(), name="document_download"),
    path("<int:pk>/upload/", views.DocumentUploadView.as_view(), name="document_upload"),
]
