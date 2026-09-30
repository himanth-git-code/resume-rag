from django.conf import settings

from apps.ai.errors import AIPermanentError

from .base import AIProvider, StructuredResult

__all__ = ["AIProvider", "StructuredResult", "get_provider"]


def get_provider() -> AIProvider:
    """The configured provider (settings.AI_PROVIDER)."""
    if settings.AI_PROVIDER == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.AI_MODEL,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
    if settings.AI_PROVIDER == "fake":
        from .fake import FakeProvider

        return FakeProvider()
    raise AIPermanentError(f"Unknown AI_PROVIDER: {settings.AI_PROVIDER!r}")
