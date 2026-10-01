from typing import Literal

from pydantic import BaseModel, Field


class ChatAnswer(BaseModel):
    answer: str = Field(description="Concise answer in the third person, using only the evidence")
    status: Literal["answered", "not_found", "declined"] = Field(
        description="answered: supported by evidence; not_found: the evidence doesn't cover it; "
        "declined: off-topic, or about personal or protected attributes"
    )
    citations: list[str] = Field(default_factory=list, description="Refs of the evidence items the answer relies on")
