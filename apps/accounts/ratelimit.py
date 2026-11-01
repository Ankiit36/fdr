"""Login rate limiting utilities using Django's cache framework."""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def client_ip(request):
    """Return the client's IP address.

    Uses REMOTE_ADDR by default. If settings.LOGIN_RATE_LIMIT_TRUST_PROXY is True,
    inspects HTTP_X_FORWARDED_FOR.
    """
    if settings.LOGIN_RATE_LIMIT_TRUST_PROXY:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def rate_key(username, ip):
    """Return 'login-fail:' + sha256 hex of '<username.lower()>|<ip>'."""
    raw = f"{str(username).lower()}|{str(ip)}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"login-fail:{h}"


def _lock_key(username, ip):
    """Return 'login-lock:' + sha256 hex of '<username.lower()>|<ip>'."""
    raw = f"{str(username).lower()}|{str(ip)}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"login-lock:{h}"


def is_locked(username, ip) -> bool:
    """Return True if cache key 'login-lock:' + same hash exists."""
    return bool(cache.get(_lock_key(username, ip)))


def record_failure(username, ip):
    """Increment a failure counter with atomic cache.add then cache.incr pattern.

    When count reaches settings.LOGIN_RATE_LIMIT_ATTEMPTS, set the lock key
    with timeout=settings.LOGIN_RATE_LIMIT_LOCK_SECONDS and delete failure counter.
    """
    fail_k = rate_key(username, ip)
    window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    lock_seconds = settings.LOGIN_RATE_LIMIT_LOCK_SECONDS
    max_attempts = settings.LOGIN_RATE_LIMIT_ATTEMPTS

    if cache.add(fail_k, 1, timeout=window):
        count = 1
    else:
        try:
            count = cache.incr(fail_k)
        except ValueError:
            cache.set(fail_k, 1, timeout=window)
            count = 1

    if count >= max_attempts:
        cache.set(_lock_key(username, ip), True, timeout=lock_seconds)
        cache.delete(fail_k)
        raw = f"{str(username).lower()}|{str(ip)}"
        user_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        logger.warning(
            "Login rate limit locked for user_hash=%s from ip=%s",
            user_hash,
            ip,
        )


def clear_failures(username, ip):
    """Delete the failure counter and lock key."""
    cache.delete(rate_key(username, ip))
    cache.delete(_lock_key(username, ip))
