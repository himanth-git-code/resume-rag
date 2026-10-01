from django.conf import settings

from apps.ai.errors import AIPermanentError

from .base import AIProvider, StructuredResult

__all__ = ["AIProvider", "StructuredResult", "get_embedding_provider", "get_provider"]


def get_provider(model: str | None = None) -> AIProvider:
    """The configured provider (settings.AI_PROVIDER), on `model` or settings.AI_MODEL."""
    if settings.AI_PROVIDER == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=model or settings.AI_MODEL,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
    if settings.AI_PROVIDER == "fake":
        from .fake import FakeProvider

        return FakeProvider()
    raise AIPermanentError(f"Unknown AI_PROVIDER: {settings.AI_PROVIDER!r}")


def get_embedding_provider() -> AIProvider:
    """The configured embeddings provider (settings.EMBEDDING_PROVIDER).

    Separate from get_provider() because generation and embeddings can come
    from different vendors (Anthropic has no embeddings API).
    """
    if settings.EMBEDDING_PROVIDER == "voyage":
        from .voyage import VoyageEmbeddingProvider

        return VoyageEmbeddingProvider(
            api_key=settings.VOYAGE_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
    if settings.EMBEDDING_PROVIDER == "fake":
        from .fake import FakeEmbeddingProvider

        return FakeEmbeddingProvider(dimensions=settings.EMBEDDING_DIMENSIONS)
    raise AIPermanentError(f"Unknown EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER!r}")
