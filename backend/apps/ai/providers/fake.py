import hashlib
import math

from .base import AIProvider, SchemaT, StructuredResult


class FakeProvider(AIProvider):
    """Deterministic provider for tests and for running without an API key.

    Structured calls return `canned[schema]` if set, otherwise an empty
    instance of the schema (every field at its default), so no facts are made up.
    """

    name = "fake"
    model = "fake"

    def __init__(self, canned: dict | None = None):
        self.canned = canned or {}
        self.calls: list[dict] = []

    def generate(self, *, system: str, prompt: str) -> str:
        self.calls.append({"system": system, "prompt": prompt})
        return ""

    def generate_structured(
        self, *, system: str, prompt: str, schema: type[SchemaT]
    ) -> StructuredResult[SchemaT]:
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        output = self.canned.get(schema) or schema()
        return StructuredResult(output=output, model=self.model)


class FakeEmbeddingProvider(AIProvider):
    """Deterministic embeddings without an API: the same text always gives the same unit vector.

    Vectors come from hashed word counts, so texts sharing words are closer,
    which is enough for tests to exercise ranking and scoping.
    """

    name = "fake"
    model = "fake-embedding"

    def __init__(self, dimensions: int = 1024):
        self.dimensions = dimensions
        self.calls: list[dict] = []

    def generate(self, *, system: str, prompt: str) -> str:
        raise NotImplementedError

    def generate_structured(self, *, system, prompt, schema):
        raise NotImplementedError

    def embed(self, texts: list[str], *, input_type: str = "document") -> list[list[float]]:
        self.calls.append({"texts": list(texts), "input_type": input_type})
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in text.lower().split():
            digest = hashlib.sha256(word.strip(".,:;()").encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
