"""
Base settings for the AICTE Security Deposit / FDR Management Portal.

Shared settings for all environments (development, staging, production).
Environment specific overrides live in ``config/settings/dev.py`` and
``config/settings/prod.py``.

All secrets and environment specific values must be provided through
environment variables (see ``.env.example`` at the project root).
"""

import os
from decimal import Decimal
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    """Return the value of an environment variable or the provided default."""
    return os.environ.get(key, default)


DEBUG = env("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes", "on")

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-fdr-portal-dev-secret-key"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY environment variable is required when DEBUG is False."
        )

ALLOWED_HOSTS = [
    host.strip()
    for host in env("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
elif DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        },
    }
else:
    raise ImproperlyConfigured(
        "DATABASE_URL environment variable is required when DEBUG is False."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts",
    "apps.institutions",
    "apps.deposits",
    "apps.documents",
    "apps.verification",
    "apps.notifications",
    "apps.audit",
    "apps.dashboard",
    "apps.agent",
    "apps.releases",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.notifications.context_processors.unread_notifications",
                "apps.core.context_processors.language",
            ],
        },
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes", "on")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@fdr-portal.local")

# Custom user model must be set before the first migration is created.
AUTH_USER_MODEL = "accounts.User"

# Number of days before maturity when reminders are triggered.
REMINDER_WINDOW_DAYS = int(env("REMINDER_WINDOW_DAYS", 30))

# AWS S3 settings (used by django-storages in production)
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "us-east-1")

# Where users are sent after logging out.
LOGOUT_REDIRECT_URL = "/accounts/login/"
LOGIN_URL = "/accounts/login/"

# Login rate limiting settings
LOGIN_RATE_LIMIT_ATTEMPTS = int(env("LOGIN_RATE_LIMIT_ATTEMPTS", 5))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(env("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300))
LOGIN_RATE_LIMIT_LOCK_SECONDS = int(env("LOGIN_RATE_LIMIT_LOCK_SECONDS", 900))
LOGIN_RATE_LIMIT_TRUST_PROXY = env(
    "LOGIN_RATE_LIMIT_TRUST_PROXY", "False"
).lower() in ("true", "1", "yes", "on")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "fdr-login",
    }
}

# Maximum document upload size in megabytes.
MAX_DOCUMENT_SIZE_MB = int(env("MAX_DOCUMENT_SIZE_MB", 5))

# Agent review settings
AGENT_AMOUNT_TOLERANCE = Decimal(env("AGENT_AMOUNT_TOLERANCE", "0"))
AGENT_HIGH_VALUE_AMOUNT = Decimal(env("AGENT_HIGH_VALUE_AMOUNT", "1000000"))
AGENT_ESCALATION_DAYS = int(env("AGENT_ESCALATION_DAYS", 7))
AGENT_EDITOR_KEYWORDS = env(
    "AGENT_EDITOR_KEYWORDS",
    "Photoshop,GIMP,Canva,iLovePDF,Smallpdf,PDF-XChange",
).split(",")


# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Spectacular (Swagger) settings
SPECTACULAR_SETTINGS = {
    "TITLE": "AICTE FDR Management API",
    "VERSION": "1.0.0",
}
