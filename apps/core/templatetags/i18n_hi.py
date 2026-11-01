"""Template tag for custom Hindi/English dictionary translations."""

from django import template

from apps.core.translations import TRANSLATIONS

register = template.Library()


@register.simple_tag(takes_context=True)
def tr(context, key: str) -> str:
    """Look up key in TRANSLATIONS for context['LANG'] or return English/key."""
    lang = context.get("LANG", "en") if context else "en"
    entry = TRANSLATIONS.get(key)
    if entry and isinstance(entry, dict):
        val = entry.get(lang)
        if val:
            return val
        en_val = entry.get("en")
        if en_val:
            return en_val
    return key
