"""API permission classes reusing the existing role helpers."""

from rest_framework.permissions import BasePermission

from apps.accounts.permissions import is_admin, is_officer, is_institution_user


class IsAdminRole(BasePermission):
    """Allow access only to ADMIN role users."""

    def has_permission(self, request, view):
        return is_admin(request.user)


class IsOfficerOrAdmin(BasePermission):
    """Allow access to OFFICER or ADMIN role users."""

    def has_permission(self, request, view):
        return is_officer(request.user) or is_admin(request.user)


class IsInstitutionOrStaff(BasePermission):
    """Allow access to INSTITUTION, OFFICER, or ADMIN role users."""

    def has_permission(self, request, view):
        return (
            is_institution_user(request.user)
            or is_officer(request.user)
            or is_admin(request.user)
        )