from dataclasses import asdict, dataclass

from django.db import transaction

from apps.resume_parser.models import ResumeParseJob
from apps.resume_parser.services import ResumeProcessingService

from .models import (
    CandidateAchievement,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLink,
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
                {"source_type": item.source_type, **{f: _from_db(f, getattr(item, f)) for f in fields}}
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
            draft[key] = [{**item, "source_type": SourceType.RESUME} for item in draft.get(key) or []]
        return draft

    @staticmethod
    def save(user, data: dict, job: ResumeParseJob | None = None) -> dict:
        """Replace the candidate's profile with `data` (validated by SaveProfileSerializer).

        The only code path that writes profile rows. Runs in one transaction:
        on any error nothing changes. `job` must belong to `user`.
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
                model.objects.filter(profile=profile).delete()
                model.objects.bulk_create(
                    model(
                        profile=profile,
                        order=index,
                        source_type=item.get("source_type") or SourceType.CANDIDATE_INPUT,
                        source_document=(
                            profile.source_document if item.get("source_type") == SourceType.RESUME else None
                        ),
                        **{f: _to_db(f, item.get(f)) for f in fields},
                    )
                    for index, item in enumerate(data.get(key) or [])
                )

            if job is not None and job.status != ResumeParseJob.Status.APPLIED:
                ResumeParseJob.objects.filter(pk=job.pk).update(status=ResumeParseJob.Status.APPLIED)

        return CandidateProfileService.serialize(profile)


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
