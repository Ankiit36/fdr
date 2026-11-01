"""Permission helpers for the AICTE FDR Management Portal."""

from functools import wraps

from django.core.exceptions import PermissionDenied

from apps.accounts.models import User


def is_admin(user):
    """Return True if the user is an authenticated ADMIN."""
    return bool(user and user.is_authenticated and user.role == User.Roles.ADMIN)


def is_officer(user):
    """Return True if the user is an authenticated OFFICER."""
    return bool(user and user.is_authenticated and user.role == User.Roles.OFFICER)


def is_institution_user(user):
    """Return True if the user is an authenticated INSTITUTION user."""
    return bool(user and user.is_authenticated and user.role == User.Roles.INSTITUTION)


def require_roles(*roles):
    """Decorator that requires the requesting user to hold one of the given roles."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated or user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
