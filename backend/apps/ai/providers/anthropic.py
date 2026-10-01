import logging

import anthropic
from pydantic import ValidationError

from apps.ai.errors import AIOutputError, AIPermanentError, AITransientError

from .base import AIProvider, SchemaT, StructuredResult

logger = logging.getLogger(__name__)

# Server-side refusal fallback: if the model declines, the API re-runs the same
# request on Anthropic's recommended fallback model within the same call. Its
# targets are Opus-class models, so it's only requested for Opus/Fable models.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODEL_PREFIXES = ("claude-opus-5", "claude-fable-5")
MAX_TOKENS = 16000


def _fallback_kwargs(model: str) -> dict:
    if model.startswith(FALLBACK_MODEL_PREFIXES):
        return {"betas": [FALLBACK_BETA], "fallbacks": "default"}
    return {}


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, *, api_key: str, model: str, timeout: float, client: anthropic.Anthropic | None = None):
        if client is None and not api_key:
            raise AIPermanentError("ANTHROPIC_API_KEY is not configured")
        self.model = model
        # Retries are owned by Celery, so the SDK fails fast and reports clearly.
        self.client = client or anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=0)

    def generate(self, *, system: str, prompt: str) -> str:
        with _translate_errors():
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                **_fallback_kwargs(self.model),
            )
        _check_stop_reason(response)
        return "".join(block.text for block in response.content if block.type == "text")

    def generate_structured(
        self, *, system: str, prompt: str, schema: type[SchemaT]
    ) -> StructuredResult[SchemaT]:
        with _translate_errors():
            try:
                response = self.client.beta.messages.parse(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=schema,
                    thinking={"type": "adaptive"},
                    **_fallback_kwargs(self.model),
                )
            except ValidationError as exc:
                raise AIOutputError("Model output did not match the schema", reason="schema_mismatch") from exc

        _check_stop_reason(response)
        if response.parsed_output is None:
            raise AIOutputError("Model returned no structured output", reason="empty")

        logger.info(
            "AI structured call ok: model=%s input_tokens=%s output_tokens=%s",
            response.model,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return StructuredResult(output=response.parsed_output, model=response.model)


def _check_stop_reason(response) -> None:
    if response.stop_reason == "refusal":
        category = getattr(response.stop_details, "category", None)
        raise AIOutputError(f"Model declined the request (category={category})", reason="refusal")
    if response.stop_reason == "max_tokens":
        raise AIOutputError("Model output was truncated", reason="max_tokens")


class _translate_errors:
    """Map SDK exceptions onto transient vs permanent AI errors."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is None or not isinstance(exc, anthropic.AnthropicError):
            return False
        if isinstance(exc, (anthropic.RateLimitError, anthropic.APIConnectionError)):
            raise AITransientError(type(exc).__name__) from exc
        if isinstance(exc, anthropic.APIStatusError):
            if exc.status_code >= 500 or exc.status_code in (408, 409):
                raise AITransientError(f"{type(exc).__name__} ({exc.status_code})") from exc
            raise AIPermanentError(f"{type(exc).__name__} ({exc.status_code})") from exc
        raise AIPermanentError(type(exc).__name__) from exc
