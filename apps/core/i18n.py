"""Internationalization helpers for English and Hindi."""

SUPPORTED = ("en", "hi")


def get_language(request) -> str:
    """Retrieve the current language code from query parameter or session.

    Defaults to 'en' if not set or unsupported.
    """
    if request is None:
        return "en"

    lang_param = getattr(request, "GET", {}).get("lang")
    if lang_param in SUPPORTED:
        return lang_param

    if hasattr(request, "session"):
        session_lang = request.session.get("lang")
        if session_lang in SUPPORTED:
            return session_lang

    return "en"


def t(key: str, request=None, default: str | None = None) -> str:
    """Translate a dictionary key for the given request language.

    Falls back to English if the translation is missing, or key if unmapped.
    """
    from apps.core.translations import TRANSLATIONS

    lang = get_language(request)
    entry = TRANSLATIONS.get(key)
    if entry and isinstance(entry, dict):
        val = entry.get(lang)
        if val:
            return val
        en_val = entry.get("en")
        if en_val:
            return en_val

    return default if default is not None else key
