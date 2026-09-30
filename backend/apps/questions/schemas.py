"""Structured output for one question-generation call."""

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["general", "technical", "experience", "project", "behavioral", "domain"]
Difficulty = Literal["foundational", "intermediate", "advanced"]


class TalkingPoint(BaseModel):
    ref: str = Field(description="Ref of one of the candidate's profile items given in the prompt")
    text: str = Field(description="What from that item the candidate could draw on, stated only as the item states it")


class FollowUp(BaseModel):
    text: str
    difficulty: Difficulty
    talking_points: list[TalkingPoint] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    category: Category
    topic: str = Field(description="Short topic, e.g. 'Caching', 'Acme Corp', 'Leadership'")
    text: str
    difficulty: Difficulty
    refs: list[str] = Field(default_factory=list, description="Refs of the profile items this question is about")
    talking_points: list[TalkingPoint] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list, description="Deep-dive follow-ups, if any")


class QuestionBatch(BaseModel):
    questions: list[GeneratedQuestion] = Field(default_factory=list)
