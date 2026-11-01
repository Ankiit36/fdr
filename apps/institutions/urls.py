"""URL patterns for the institutions app."""

from django.urls import path

from apps.institutions import views

urlpatterns = [
    path("", views.InstitutionListView.as_view(), name="institution_list"),
    path("new/", views.InstitutionCreateView.as_view(), name="institution_create"),
    path("<int:pk>/edit/", views.InstitutionUpdateView.as_view(), name="institution_update"),
    path("<int:pk>/deactivate/", views.InstitutionDeactivateView.as_view(), name="institution_deactivate"),
]
