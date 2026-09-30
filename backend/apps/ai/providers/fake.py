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
