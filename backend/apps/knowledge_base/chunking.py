"""Render a candidate's approved profile and notes as retrieval chunks.

Deterministic: the same data always yields the same chunks (and hashes), so a
rebuild only re-embeds what actually changed. Only candidate-approved data is
used; the raw resume text is deliberately excluded (SPEC §10).
"""

import hashlib
from dataclasses import dataclass

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

from .models import KnowledgeChunk

ST = KnowledgeChunk.SourceType
NOTE_CHUNK_CHARS = 1500


@dataclass(frozen=True)
class ChunkSpec:
    key: str
    source_type: str
    source_id: int | None
    text: str

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()


def _lines(*pairs) -> str:
    return "\n".join(f"{label}: {value}" for label, value in pairs if value)


def _join(values) -> str:
    return ", ".join(v for v in values if v)


def _bullets(values) -> str:
    return "; ".join(v for v in values if v)


def _period(start, end, current=None) -> str:
    end = end or ("Present" if current else "")
    return " – ".join(v for v in (start, end) if v)


def build_chunks(user) -> list[ChunkSpec]:
    chunks: list[ChunkSpec] = []
    profile = CandidateProfile.objects.filter(user=user).first()

    if profile is not None:
        basics = _lines(
            ("Name", profile.full_name),
            ("Headline", profile.headline),
            ("Location", profile.location),
            ("Summary", profile.summary),
        )
        if basics:
            chunks.append(ChunkSpec("profile", ST.PROFILE, profile.pk, basics))

        for e in CandidateExperience.objects.filter(profile=profile).order_by("order", "pk"):
            role = " at ".join(v for v in (e.title, e.company) if v)
            text = _lines(
                ("Experience", role),
                ("Period", _period(e.start_date, e.end_date, e.is_current)),
                ("Location", e.location),
                ("Description", e.description),
                ("Responsibilities", _bullets(e.responsibilities)),
                ("Achievements", _bullets(e.achievements)),
                ("Technologies", _join(e.technologies)),
            )
            chunks.append(ChunkSpec(f"experience:{e.pk}", ST.EXPERIENCE, e.pk, text))

        for p in CandidateProject.objects.filter(profile=profile).order_by("order", "pk"):
            text = _lines(
                ("Project", p.name),
                ("Role", p.role),
                ("Period", _period(p.start_date, p.end_date)),
                ("Description", p.description),
                ("Technologies", _join(p.technologies)),
                ("Link", p.url),
            )
            chunks.append(ChunkSpec(f"project:{p.pk}", ST.PROJECT, p.pk, text))

        for ed in CandidateEducation.objects.filter(profile=profile).order_by("order", "pk"):
            text = _lines(
                ("Education", _join([ed.degree, ed.field_of_study])),
                ("Institution", ed.institution),
                ("Period", _period(ed.start_date, ed.end_date)),
                ("Grade", ed.grade),
            )
            chunks.append(ChunkSpec(f"education:{ed.pk}", ST.EDUCATION, ed.pk, text))

        for c in CandidateCertification.objects.filter(profile=profile).order_by("order", "pk"):
            text = _lines(
                ("Certification", c.name),
                ("Issuer", c.issuer),
                ("Issued", c.issue_date),
                ("Expires", c.expiry_date),
                ("Credential ID", c.credential_id),
            )
            chunks.append(ChunkSpec(f"certification:{c.pk}", ST.CERTIFICATION, c.pk, text))

        for a in CandidateAchievement.objects.filter(profile=profile).order_by("order", "pk"):
            text = _lines(("Achievement", a.title), ("Date", a.date), ("Description", a.description))
            chunks.append(ChunkSpec(f"achievement:{a.pk}", ST.ACHIEVEMENT, a.pk, text))

        groups: dict[str, list[str]] = {}
        for s in CandidateSkill.objects.filter(profile=profile).order_by("order", "pk"):
            groups.setdefault(s.category or "", []).append(s.name)
        for category, names in groups.items():
            label = f"Skills ({category})" if category else "Skills"
            chunks.append(ChunkSpec(f"skills:{category or '-'}", ST.SKILLS, None, f"{label}: {_join(names)}"))

    for note in CandidateNote.objects.filter(user=user).order_by("pk"):
        for index, part in enumerate(_split(note.body, NOTE_CHUNK_CHARS)):
            text = _lines(("Note", note.title), ("Content", part))
            chunks.append(ChunkSpec(f"note:{note.pk}:{index}", ST.NOTE, note.pk, text))

    return chunks


def _split(text: str, limit: int) -> list[str]:
    """Split on paragraph boundaries into pieces of at most ~`limit` characters."""
    pieces, current = [], ""
    for paragraph in (p.strip() for p in text.split("\n\n")):
        if not paragraph:
            continue
        while len(paragraph) > limit:  # a single very long paragraph
            pieces.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        if current and len(current) + len(paragraph) + 2 > limit:
            pieces.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        pieces.append(current)
    return pieces
