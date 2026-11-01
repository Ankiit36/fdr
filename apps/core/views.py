"""Views for core app and language switching."""

from django.http import HttpResponseRedirect

from apps.core.i18n import SUPPORTED


def set_language_view(request, code: str):
    """Set the active language in the session and redirect back."""
    if code in SUPPORTED:
        request.session["lang"] = code
    referer = request.META.get("HTTP_REFERER") or "/"
    return HttpResponseRedirect(referer)
