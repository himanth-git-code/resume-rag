from typing import Literal

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    text: str = Field(description="One requirement, in the job description's own words where possible")
    importance: Literal["required", "preferred"]


class RequirementList(BaseModel):
    job_title: str | None = Field(None, description="The job title, if the description states one")
    requirements: list[Requirement] = Field(default_factory=list)


class Assessment(BaseModel):
    index: int = Field(description="Number of the requirement being assessed")
    status: Literal["met", "partial", "no_evidence"]
    evidence_refs: list[str] = Field(default_factory=list, description="Refs of the evidence items that support it")
    explanation: str = Field(description="One sentence restating what the cited evidence shows")


class AssessmentList(BaseModel):
    assessments: list[Assessment] = Field(default_factory=list)
