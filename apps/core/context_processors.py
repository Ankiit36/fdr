"""Template context processor for active UI language."""

from apps.core.i18n import get_language


def language(request):
    """Expose LANG in template contexts."""
    return {
        "LANG": get_language(request),
    }
