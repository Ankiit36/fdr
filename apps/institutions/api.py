"""API viewsets for the Institutions app."""

from rest_framework import viewsets

from apps.accounts.api_permissions import IsAdminRole, IsOfficerOrAdmin
from apps.institutions.models import Institution
from apps.institutions.serializers import InstitutionSerializer


class InstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for institutions.

    ADMIN and OFFICER see all institutions.
    INSTITUTION sees only its own institution.
    A user with no institution sees empty results.
    """

    serializer_class = InstitutionSerializer
    permission_classes = [IsOfficerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Institution.objects.none()
        if user.role == "ADMIN" or user.role == "OFFICER":
            return Institution.objects.all().order_by("pk")
        if user.role == "INSTITUTION":
            if user.institution_id:
                return Institution.objects.filter(pk=user.institution_id).order_by("pk")
            return Institution.objects.none()
        return Institution.objects.none()