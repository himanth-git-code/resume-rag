import logging

import requests

from apps.ai.errors import AIOutputError, AIPermanentError, AITransientError

from .base import AIProvider

logger = logging.getLogger(__name__)

API_URL = "https://api.voyageai.com/v1/embeddings"
# Well under Voyage's limits (1,000 texts / 320K tokens per request for voyage-4).
BATCH_SIZE = 128


class VoyageEmbeddingProvider(AIProvider):
    """Voyage AI embeddings over its REST API.

    A thin client on `requests` rather than the voyageai SDK, which pulls in
    numpy, pillow, tokenizers, aiohttp and more to wrap this one endpoint.
    """

    name = "voyage"

    def __init__(self, *, api_key: str, model: str, dimensions: int, timeout: float, session=None):
        if not api_key:
            raise AIPermanentError("VOYAGE_API_KEY is not configured")
        self.model = model
        self.dimensions = dimensions
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    def generate(self, *, system: str, prompt: str) -> str:
        raise NotImplementedError("Voyage provides embeddings only")

    def generate_structured(self, *, system, prompt, schema):
        raise NotImplementedError("Voyage provides embeddings only")

    def embed(self, texts: list[str], *, input_type: str = "document") -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            vectors.extend(self._embed_batch(texts[start : start + BATCH_SIZE], input_type))
        return vectors

    def _embed_batch(self, texts: list[str], input_type: str) -> list[list[float]]:
        body = {
            "input": texts,
            "model": self.model,
            "input_type": input_type,
            "output_dimension": self.dimensions,
        }
        try:
            response = self.session.post(API_URL, json=body, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise AITransientError(type(exc).__name__) from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise AITransientError(f"Voyage API error ({response.status_code})")
        if response.status_code >= 400:
            raise AIPermanentError(f"Voyage API error ({response.status_code})")

        try:
            payload = response.json()
            data = sorted(payload["data"], key=lambda item: item["index"])
            vectors = [item["embedding"] for item in data]
        except (ValueError, KeyError, TypeError) as exc:
            raise AIOutputError("Unexpected Voyage response", reason="malformed") from exc

        if len(vectors) != len(texts) or any(len(v) != self.dimensions for v in vectors):
            raise AIOutputError("Voyage returned the wrong number or size of vectors", reason="malformed")

        logger.info("Voyage embed ok: model=%s texts=%s tokens=%s", self.model, len(texts), payload.get("usage", {}).get("total_tokens"))
        return vectors
