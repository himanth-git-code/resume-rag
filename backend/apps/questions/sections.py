"""Split a candidate's approved profile and notes into question-generation sections.

Each section is one model call over a small set of profile items. Items carry a
ref ("experience:12", "skill:4", "note:3"); the model may only cite those refs,
and anything it cites outside the section is dropped.
"""

import hashlib
import json
from dataclasses import dataclass, field

from apps.candidates.models import (
    CandidateAchievement,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateNote,
    CandidateProfile,
    CandidateProject,
    CandidateSkill,
)

from .models import Question

C = Question.Category


@dataclass(frozen=True)
class Item:
    ref: str
    label: str
    text: str


@dataclass(frozen=True)
class Section:
    key: str
    title: str
    categories: tuple[str, ...]
    focus: str
    items: tuple[Item, ...]
    count: int = 8
    avoid: tuple[str, ...] = field(default_factory=tuple)

    @property
    def refs(self) -> set[str]:
        return {item.ref for item in self.items}


def _lines(*pairs) -> str:
    return "\n".join(f"{label}: {value}" for label, value in pairs if value)


def _period(start, end, current=None) -> str:
    end = end or ("Present" if current else "")
    return " – ".join(v for v in (start, end) if v)


class ProfileItems:
    """All of a candidate's items, keyed by ref."""

    def __init__(self, user):
        self.profile = CandidateProfile.objects.filter(user=user).first()
        self.by_ref: dict[str, Item] = {}
        self.experience: list[Item] = []
        self.projects: list[Item] = []
        self.skills: list[Item] = []
        self.background: list[Item] = []  # education, certifications, achievements
        self.notes: list[Item] = []
        if self.profile is None:
            return

        p = self.profile
        basics = _lines(("Name", p.full_name), ("Headline", p.headline), ("Location", p.location), ("Summary", p.summary))
        self._add(self.background, "profile", "Your profile summary", basics or "No summary given.")

        for e in CandidateExperience.objects.filter(profile=p).order_by("order", "pk"):
            label = " at ".join(v for v in (e.title, e.company) if v) or "Role"
            text = _lines(
                ("Role", label),
                ("Period", _period(e.start_date, e.end_date, e.is_current)),
                ("Location", e.location),
                ("Description", e.description),
                ("Responsibilities", "; ".join(e.responsibilities)),
                ("Achievements", "; ".join(e.achievements)),
                ("Technologies", ", ".join(e.technologies)),
            )
            self._add(self.experience, f"experience:{e.pk}", label, text)

        for pr in CandidateProject.objects.filter(profile=p).order_by("order", "pk"):
            text = _lines(
                ("Project", pr.name),
                ("Role", pr.role),
                ("Period", _period(pr.start_date, pr.end_date)),
                ("Description", pr.description),
                ("Technologies", ", ".join(pr.technologies)),
            )
            self._add(self.projects, f"project:{pr.pk}", f"Project: {pr.name}", text)

        for s in CandidateSkill.objects.filter(profile=p).order_by("order", "pk"):
            text = f"Skill: {s.name}" + (f" (category: {s.category})" if s.category else "")
            self._add(self.skills, f"skill:{s.pk}", s.name, text)

        for ed in CandidateEducation.objects.filter(profile=p).order_by("order", "pk"):
            label = ", ".join(v for v in (ed.degree, ed.institution) if v) or "Education"
            text = _lines(("Education", label), ("Field", ed.field_of_study), ("Period", _period(ed.start_date, ed.end_date)))
            self._add(self.background, f"education:{ed.pk}", label, text)

        for c in CandidateCertification.objects.filter(profile=p).order_by("order", "pk"):
            self._add(self.background, f"certification:{c.pk}", c.name, _lines(("Certification", c.name), ("Issuer", c.issuer)))

        for a in CandidateAchievement.objects.filter(profile=p).order_by("order", "pk"):
            self._add(self.background, f"achievement:{a.pk}", a.title, _lines(("Achievement", a.title), ("Details", a.description)))

        for n in CandidateNote.objects.filter(user=user).order_by("pk"):
            self._add(self.notes, f"note:{n.pk}", f"Note: {n.title}", _lines(("Note", n.title), ("Content", n.body)))

    def _add(self, bucket, ref, label, text):
        item = Item(ref=ref, label=label, text=text)
        bucket.append(item)
        self.by_ref[ref] = item

    @property
    def exists(self) -> bool:
        return self.profile is not None

    def fingerprint(self) -> str:
        """Changes whenever anything the questions are based on changes."""
        payload = [(i.ref, i.text) for i in self.by_ref.values()]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _brief(text: str) -> str:
    return "\n".join(text.splitlines()[:2])


def plan_full(items: ProfileItems) -> list[str]:
    keys = ["overview"]
    if items.skills:
        keys.append("skills")
    keys += [i.ref for i in items.experience]
    keys += [i.ref for i in items.projects]
    return keys


def build_section(key: str, items: ProfileItems) -> Section | None:
    """The section for `key` from current data, or None if its item no longer exists."""
    # Overview and skills sections see each role briefly (title and period), not its full detail.
    role_summaries = tuple(Item(i.ref, i.label, _brief(i.text)) for i in items.experience)

    if key == "overview":
        return Section(
            key=key,
            title="Career overview",
            categories=(C.GENERAL, C.BEHAVIORAL, C.DOMAIN),
            focus=(
                "career background, walking through the resume, education, career progression and motivation; "
                "behavioral questions (leadership, teamwork, conflict, communication, decision making, failure, "
                "mentoring, ownership, stakeholder management) grounded in the roles listed; and domain questions "
                "suited to the candidate's industry, role and seniority."
            ),
            items=tuple(items.background) + role_summaries + tuple(items.notes),
            count=12,
        )
    if key == "skills":
        return Section(
            key=key,
            title="Skills",
            categories=(C.TECHNICAL,),
            focus=(
                "technical questions on the listed skills (languages, frameworks, databases, cloud, DevOps, "
                "architecture, security, testing), from fundamentals to advanced, tailored to the candidate's level."
            ),
            items=tuple(items.skills) + role_summaries,
            count=12,
        )
    item = items.by_ref.get(key)
    if item is None:
        return None
    if key.startswith("experience:"):
        return Section(
            key=key,
            title=item.label,
            categories=(C.EXPERIENCE, C.TECHNICAL, C.BEHAVIORAL),
            focus=(
                "this role: responsibilities, achievements, challenges, decisions and technical implementations. "
                "For each concrete claim (e.g. 'introduced Redis caching to cut latency'), ask about it and add "
                "deep-dive follow-ups an interviewer would ask next: why it was needed, why that approach, "
                "alternatives, how it was measured, what went wrong."
            ),
            items=(item,),
            count=8,
        )
    if key.startswith("project:"):
        return Section(
            key=key,
            title=item.label,
            categories=(C.PROJECT, C.TECHNICAL),
            focus=(
                "this project: overview, the candidate's responsibility, architecture, technologies, challenges, "
                "decisions and trade-offs, failures, results, performance, scalability, security and lessons "
                "learned, with deep-dive follow-ups on specific claims."
            ),
            items=(item,),
            count=8,
        )
    return None


def build_more_section(scope: dict, items: ProfileItems, existing: list[str]) -> Section | None:
    """A small section for "generate more", narrowed by category and/or source item."""
    source, category = scope.get("source"), scope.get("category")
    if source:
        base = build_section(source, items)
        if base is None and source in items.by_ref:  # e.g. a skill or note
            item = items.by_ref[source]
            base = Section(
                key=source,
                title=item.label,
                categories=tuple(C.values),
                focus=f"questions about '{item.label}'.",
                items=(item,),
            )
    elif category in (C.TECHNICAL,):
        base = build_section("skills", items)
    else:
        base = build_section("overview", items)
    if base is None:
        return None
    categories = (category,) if category else base.categories
    return Section(
        key=f"more:{source or category or 'any'}",
        title=base.title,
        categories=categories,
        focus=base.focus,
        items=base.items,
        count=5,
        avoid=tuple(existing[:100]),
    )
