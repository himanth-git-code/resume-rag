class AIError(Exception):
    """Base class for AI provider failures. Messages never contain candidate data."""


class AITransientError(AIError):
    """Temporary failure (rate limit, overload, network, 5xx). Safe to retry."""


class AIPermanentError(AIError):
    """Failure that retrying won't fix (bad request, auth, configuration)."""


class AIOutputError(AIPermanentError):
    """The model answered, but not with usable output (refusal, truncation, schema mismatch)."""

    def __init__(self, message: str, *, reason: str):
        super().__init__(message)
        self.reason = reason
