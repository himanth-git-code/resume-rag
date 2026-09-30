from types import SimpleNamespace
from unittest import mock

import anthropic
import httpx2
import pytest

from apps.ai.errors import AIOutputError, AIPermanentError, AITransientError
from apps.ai.providers.anthropic import AnthropicProvider
from apps.resume_parser.schemas import ResumeExtraction


def make_provider(parse):
    client = mock.Mock()
    client.beta.messages.parse = parse
    return AnthropicProvider(api_key="", model="claude-opus-5", timeout=10, client=client), client


def response(stop_reason="end_turn", parsed=None, category=None):
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category=category) if category else None,
        parsed_output=parsed,
        model="claude-opus-5",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


def status_error(cls, code):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx2.Response(code, request=request), body=None)


def test_structured_call_uses_schema_adaptive_thinking_and_fallback():
    parse = mock.Mock(return_value=response(parsed=ResumeExtraction(full_name="Jane")))
    provider, _ = make_provider(parse)

    result = provider.generate_structured(system="sys", prompt="p", schema=ResumeExtraction)

    assert result.output.full_name == "Jane"
    assert result.model == "claude-opus-5"
    kwargs = parse.call_args.kwargs
    assert kwargs["model"] == "claude-opus-5"
    assert kwargs["output_format"] is ResumeExtraction
    assert kwargs["thinking"] == {"type": "adaptive"}
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]


@pytest.mark.parametrize(("stop_reason", "reason"), [("refusal", "refusal"), ("max_tokens", "max_tokens")])
def test_unusable_stop_reasons_raise_output_error(stop_reason, reason):
    provider, _ = make_provider(mock.Mock(return_value=response(stop_reason=stop_reason, category="bio")))
    with pytest.raises(AIOutputError) as exc:
        provider.generate_structured(system="s", prompt="p", schema=ResumeExtraction)
    assert exc.value.reason == reason


def test_missing_parsed_output_is_an_output_error():
    provider, _ = make_provider(mock.Mock(return_value=response(parsed=None)))
    with pytest.raises(AIOutputError):
        provider.generate_structured(system="s", prompt="p", schema=ResumeExtraction)


@pytest.mark.parametrize(
    "error",
    [
        status_error(anthropic.RateLimitError, 429),
        status_error(anthropic.InternalServerError, 500),
        status_error(anthropic.APIStatusError, 529),
        anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com")),
    ],
)
def test_retryable_sdk_errors_are_transient(error):
    provider, _ = make_provider(mock.Mock(side_effect=error))
    with pytest.raises(AITransientError):
        provider.generate_structured(system="s", prompt="p", schema=ResumeExtraction)


@pytest.mark.parametrize(
    "error",
    [status_error(anthropic.BadRequestError, 400), status_error(anthropic.AuthenticationError, 401)],
)
def test_client_errors_are_permanent(error):
    provider, _ = make_provider(mock.Mock(side_effect=error))
    with pytest.raises(AIPermanentError) as exc:
        provider.generate_structured(system="s", prompt="p", schema=ResumeExtraction)
    assert not isinstance(exc.value, AITransientError)


def test_missing_api_key_is_a_configuration_error():
    with pytest.raises(AIPermanentError):
        AnthropicProvider(api_key="", model="claude-opus-5", timeout=10)
