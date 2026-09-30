from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredResult(Generic[SchemaT]):
    output: SchemaT
    model: str


class AIProvider(ABC):
    """Vendor-neutral AI interface. Business logic depends only on this class.

    Implementations raise the errors in apps.ai.errors, never vendor exceptions.
    """

    name: str

    @abstractmethod
    def generate(self, *, system: str, prompt: str) -> str:
        """Free-form text generation."""

    @abstractmethod
    def generate_structured(
        self, *, system: str, prompt: str, schema: type[SchemaT]
    ) -> StructuredResult[SchemaT]:
        """Generate output that validates against `schema`."""

    def embed(self, texts: list[str], *, input_type: str = "document") -> list[list[float]]:
        """One vector per text. `input_type` is "document" for stored content, "query" for searches."""
        raise NotImplementedError(f"{self.name} does not provide embeddings")

    def moderate(self, text: str) -> bool:
        raise NotImplementedError(f"{self.name} does not provide moderation")
