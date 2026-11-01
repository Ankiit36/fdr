"""
Development settings for the AICTE Security Deposit / FDR Management Portal.

- ``DEBUG=True``: SQLite database fallback is used.
- ``DEBUG=False``: PostgreSQL database is used.
"""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

if DEBUG:
    # SQLite fallback for local development.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        },
    }
else:  # pragma: no cover
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "fdr_portal"),
            "USER": env("DB_USER", "fdr_user"),
            "PASSWORD": env("DB_PASSWORD", "fdr_password"),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
        },
    }

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@localhost")
