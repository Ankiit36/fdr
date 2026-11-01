"""
Settings package for the AICTE Security Deposit / FDR Management Portal.
"""

import os

_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.dev")

if _settings_module in ("config.settings", "config.settings."):
    if (
        os.environ.get("DJANGO_ENV", "").lower() == "production"
        or os.environ.get("DJANGO_DEBUG", "").lower() in ("false", "0", "no")
    ):
        from .prod import *  # noqa: F401,F403
    else:
        from .dev import *  # noqa: F401,F403
