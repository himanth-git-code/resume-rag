"""Helpers shared by the unauthenticated public endpoints: client identity and bot protection."""

import hashlib
import logging

import requests
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class _ClientIP(SimpleRateThrottle):
    """Reuse DRF's proxy-aware client IP logic (honours NUM_PROXIES)."""

    rate = "1/s"

    def get_cache_key(self, request, view):  # pragma: no cover - not used for throttling
        return None


def client_ip(request) -> str:
    return _ClientIP().get_ident(request)


def ip_hash(request) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{client_ip(request)}".encode()).hexdigest()


def user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:200]


def turnstile_enabled() -> bool:
    return bool(settings.TURNSTILE_SECRET_KEY)


def verify_turnstile(token: str | None, request) -> bool:
    """True if bot protection is off, or Cloudflare confirms the token. Fails closed on errors."""
    if not turnstile_enabled():
        return True
    if not token:
        return False
    try:
        response = requests.post(
            TURNSTILE_VERIFY_URL,
            data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token, "remoteip": client_ip(request)},
            timeout=5,
        )
        return bool(response.json().get("success"))
    except (requests.RequestException, ValueError):
        logger.warning("Turnstile verification unavailable")
        return False


class PublicRateThrottle(SimpleRateThrottle):
    """Per-client-IP throttle for public endpoints; subclasses set `scope`."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class PublicViewThrottle(PublicRateThrottle):
    scope = "public_view"


class PublicChatThrottle(PublicRateThrottle):
    scope = "public_chat"


class PublicMatchThrottle(PublicRateThrottle):
    scope = "public_match"


class PublicPollThrottle(PublicRateThrottle):
    """Status polling (chat transcripts, match reports) needs a much higher ceiling."""

    scope = "public_poll"
