from dataclasses import asdict, dataclass

from django.db import transaction

from apps.audit.services import record
from apps.knowledge_base.services import KnowledgeBaseService
from apps.questions.services import QuestionGenerationService
from apps.resume_parser.models import ResumeParseJob
from apps.resume_parser.services import ResumeProcessingService

from .models import (
    CandidateAchievement,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLink,
    CandidateNote,
    CandidateProfile,
    CandidateProject,
    CandidateSkill,
    SourceType,
)

SCALAR_FIELDS = ["full_name", "headline", "summary", "email", "phone", "location"]
LIST_FIELDS = {"responsibilities", "achievements", "technologies"}

# Payload section -> (model, fields). Field names match ResumeExtraction.
SECTIONS = {
    "links": (CandidateLink, ["label", "url"]),
    "skills": (CandidateSkill, ["name", "category"]),
    "experience": (
        CandidateExperience,
        [
            "company", "title", "location", "start_date", "end_date", "is_current",
            "description", "responsibilities", "achievements", "technologies",
        ],
    ),
    "education": (CandidateEducation, ["institution", "degree", "field_of_study", "start_date", "end_date", "grade"]),
    "certifications": (
        CandidateCertification,
        ["name", "issuer", "issue_date", "expiry_date", "credential_id", "url"],
    ),
    "projects": (
        CandidateProject,
        ["name", "role", "description", "technologies", "url", "start_date", "end_date"],
    ),
    "achievements": (CandidateAchievement, ["title", "description", "date"]),
}


class DraftNotAvailable(Exception):
    """The parse job has no reviewable draft (still running, or failed)."""


def _to_db(field, value):
    if field in LIST_FIELDS:
        return [v for v in (value or []) if v]
    if field == "is_current":
        return value
    return value or ""


def _from_db(field, value):
    if field in LIST_FIELDS or field == "is_current":
        return value
    return value or None  # missing text is null on the wire, as in the AI draft


class CandidateProfileService:
    @staticmethod
    def get(user) -> dict | None:
        try:
            profile = CandidateProfile.objects.get(user=user)
        except CandidateProfile.DoesNotExist:
            return None
        return CandidateProfileService.serialize(profile)

    @staticmethod
    def serialize(profile: CandidateProfile) -> dict:
        data = {field: _from_db(field, getattr(profile, field)) for field in SCALAR_FIELDS}
        for key, (model, fields) in SECTIONS.items():
            data[key] = [
                {"id": item.pk, "source_type": item.source_type, **{f: _from_db(f, getattr(item, f)) for f in fields}}
                for item in model.objects.filter(profile=profile).order_by("order", "pk")
            ]
        data["updated_at"] = profile.updated_at.isoformat()
        return data

    @staticmethod
    def draft_for(job: ResumeParseJob) -> dict:
        """The AI draft of a job, shaped like a profile. Every item is marked as resume-sourced."""
        if job.status not in (ResumeParseJob.Status.READY_FOR_REVIEW, ResumeParseJob.Status.APPLIED) or not job.result:
            raise DraftNotAvailable
        draft = dict(job.result)
        for key in SECTIONS:
            # Draft items are new: no id, so saving creates rows rather than updating any.
            draft[key] = [{**item, "id": None, "source_type": SourceType.RESUME} for item in draft.get(key) or []]
        return draft

    @staticmethod
    def save(user, data: dict, job: ResumeParseJob | None = None) -> dict:
        """Replace the candidate's profile with `data` (validated by SaveProfileSerializer).

        The only code path that writes profile rows. Runs in one transaction:
        on any error nothing changes. `job` must belong to `user`.

        Items carrying the `id` of one of this profile's rows update that row
        (so ids stay stable for anything citing them); other items are created
        and rows missing from `data` are deleted. Ids of other profiles' rows
        are ignored, never updated.
        """
        if job is not None and job.status not in (
            ResumeParseJob.Status.READY_FOR_REVIEW,
            ResumeParseJob.Status.APPLIED,
        ):
            raise DraftNotAvailable

        with transaction.atomic():
            profile, _ = CandidateProfile.objects.select_for_update().get_or_create(user=user)
            for field in SCALAR_FIELDS:
                setattr(profile, field, _to_db(field, data.get(field)))
            if job is not None:
                profile.source_document = job.document
            profile.save()

            for key, (model, fields) in SECTIONS.items():
                _sync_section(profile, model, fields, data.get(key) or [])

            if job is not None and job.status != ResumeParseJob.Status.APPLIED:
                ResumeParseJob.objects.filter(pk=job.pk).update(status=ResumeParseJob.Status.APPLIED)

            KnowledgeBaseService.schedule_rebuild(user)
            QuestionGenerationService.schedule_initial(user)
            record("profile.updated", actor=user, subject_user=user, target=profile, from_resume=job is not None)

        return CandidateProfileService.serialize(profile)


def _sync_section(profile, model, fields, items):
    existing = {row.pk: row for row in model.objects.filter(profile=profile)}
    to_create, to_update, kept = [], [], set()

    for index, item in enumerate(items):
        source_type = item.get("source_type") or SourceType.CANDIDATE_INPUT
        values = {
            "order": index,
            "source_type": source_type,
            **{f: _to_db(f, item.get(f)) for f in fields},
        }
        row = existing.get(item.get("id"))
        if row is not None and row.pk not in kept:
            for attr, value in values.items():
                setattr(row, attr, value)
            if source_type != SourceType.RESUME:
                row.source_document = None
            to_update.append(row)
            kept.add(row.pk)
        else:
            to_create.append(
                model(
                    profile=profile,
                    source_document=profile.source_document if source_type == SourceType.RESUME else None,
                    **values,
                )
            )

    model.objects.filter(profile=profile).exclude(pk__in=kept).delete()
    if to_update:
        model.objects.bulk_update(to_update, ["order", "source_type", "source_document", *fields])
    model.objects.bulk_create(to_create)


class CandidateNoteService:
    """CRUD for a candidate's notes. Every query is scoped to `user`."""

    @staticmethod
    def list(user):
        return CandidateNote.objects.filter(user=user)

    @staticmethod
    def get(user, note_id: int) -> CandidateNote:
        return CandidateNote.objects.get(pk=note_id, user=user)

    @staticmethod
    @transaction.atomic
    def create(user, *, title: str, body: str) -> CandidateNote:
        note = CandidateNote.objects.create(user=user, title=title, body=body)
        KnowledgeBaseService.schedule_rebuild(user)
        return note

    @staticmethod
    @transaction.atomic
    def update(note: CandidateNote, *, title: str, body: str) -> CandidateNote:
        note.title, note.body = title, body
        note.save(update_fields=["title", "body", "updated_at"])
        KnowledgeBaseService.schedule_rebuild(note.user)
        return note

    @staticmethod
    @transaction.atomic
    def delete(note: CandidateNote) -> None:
        user = note.user
        note.delete()
        KnowledgeBaseService.schedule_rebuild(user)


@dataclass(frozen=True)
class DashboardState:
    has_resume: bool
    latest_parse_status: str | None
    latest_job_id: int | None
    has_profile: bool


class CandidateDashboardService:
    """Summarises where the candidate is in onboarding, for the dashboard."""

    @staticmethod
    def get_state(user) -> dict:
        job = ResumeProcessingService.latest_job_for(user)
        return asdict(
            DashboardState(
                has_resume=job is not None,
                latest_parse_status=job.status if job else None,
                latest_job_id=job.pk if job else None,
                has_profile=CandidateProfile.objects.filter(user=user).exists(),
            )
        )
