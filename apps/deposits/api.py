"""API viewsets for the Deposits app."""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.api_permissions import IsAdminRole, IsOfficerOrAdmin, IsInstitutionOrStaff
from apps.deposits.models import Deposit
from apps.deposits.serializers import DepositSerializer
from apps.deposits.services import (
    DomainError,
    create_deposit,
    delete_deposit,
    get_deposit_for_user,
    get_visible_deposits,
    update_deposit,
)


class DepositViewSet(ModelViewSet):
    """ViewSet for deposits with role-based scoping.

    - List/Retrieve: scoped via get_visible_deposits; non-visible returns 404.
    - Create: INSTITUTION can create only for its own institution;
              OFFICER is read-only; ADMIN can do everything.
    - Update: INSTITUTION can update own institution's deposits;
              OFFICER is read-only; ADMIN can do everything.
    - Delete: ADMIN only.
    """

    serializer_class = DepositSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminRole()]
        if self.action in ("create", "update", "partial_update"):
            return [IsInstitutionOrStaff()]
        return [IsInstitutionOrStaff()]

    def get_queryset(self):
        return get_visible_deposits(self.request.user).order_by("-created_at")

    def get_object(self):
        """Use get_deposit_for_user so non-visible objects return 404."""
        return get_deposit_for_user(self.request.user, self.kwargs["pk"])

    def create(self, request, *args, **kwargs):
        """Create a deposit through the service layer."""
        user = request.user
        if user.role == "OFFICER":
            return Response(
                {"detail": "Officers cannot create deposits."},
                status=status.HTTP_403_FORBIDDEN,
            )

        institution = request.data.get("institution")
        if user.role == "INSTITUTION":
            if not institution or int(institution) != user.institution_id:
                return Response(
                    {"detail": "Institutions can only create deposits for their own institution."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            deposit = create_deposit(
                institution_id=serializer.validated_data["institution"],
                instrument_type=serializer.validated_data["instrument_type"],
                reference_number=serializer.validated_data["reference_number"],
                bank_name=serializer.validated_data["bank_name"],
                bank_branch=serializer.validated_data.get("bank_branch", ""),
                amount=serializer.validated_data["amount"],
                issue_date=serializer.validated_data["issue_date"],
                maturity_date=serializer.validated_data["maturity_date"],
                created_by=user,
            )
        except DomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        out_serializer = self.get_serializer(deposit)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update a deposit through the service layer."""
        user = request.user
        if user.role == "OFFICER":
            return Response(
                {"detail": "Officers cannot update deposits."},
                status=status.HTTP_403_FORBIDDEN,
            )

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if user.role == "INSTITUTION":
            if instance.institution_id != user.institution_id:
                return Response(
                    {"detail": "Institutions can only update their own institution's deposits."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            deposit = update_deposit(
                deposit=instance,
                instrument_type=serializer.validated_data.get("instrument_type"),
                reference_number=serializer.validated_data.get("reference_number"),
                bank_name=serializer.validated_data.get("bank_name"),
                bank_branch=serializer.validated_data.get("bank_branch"),
                amount=serializer.validated_data.get("amount"),
                issue_date=serializer.validated_data.get("issue_date"),
                maturity_date=serializer.validated_data.get("maturity_date"),
            )
        except DomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        out_serializer = self.get_serializer(deposit)
        return Response(out_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete a deposit (ADMIN only)."""
        instance = self.get_object()
        delete_deposit(instance, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)