"""Structured resume extraction schema (SPEC §6).

Every field is optional: anything not written in the resume stays null/empty.
Dates are kept as written ("Jan 2020", "2019", "Present") rather than normalised,
so the model never has to guess a day or month.
"""

from pydantic import BaseModel, Field


class Link(BaseModel):
    label: str | None = Field(None, description="e.g. LinkedIn, GitHub, Portfolio")
    url: str


class Skill(BaseModel):
    name: str
    category: str | None = Field(None, description="Only if the resume groups skills, e.g. 'Languages'")


class Experience(BaseModel):
    company: str | None = None
    title: str | None = None
    location: str | None = None
    start_date: str | None = Field(None, description="As written in the resume")
    end_date: str | None = Field(None, description="As written, e.g. 'Present'")
    is_current: bool | None = Field(None, description="True only if the resume says the role is ongoing")
    description: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None


class Certification(BaseModel):
    name: str
    issuer: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    credential_id: str | None = None
    url: str | None = None


class Project(BaseModel):
    name: str
    role: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class Achievement(BaseModel):
    title: str
    description: str | None = None
    date: str | None = None


class ResumeExtraction(BaseModel):
    full_name: str | None = None
    headline: str | None = Field(None, description="Professional title or headline")
    summary: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[Link] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
