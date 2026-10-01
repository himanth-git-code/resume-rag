"""Job description matching (SPEC §10A).

The model only extracts requirements and judges each against cited evidence;
the score, strengths and gaps are computed here, so the same assessments always
give the same report and no free-text claims about the candidate are generated.
"""

import hashlib
import logging
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ai.providers import get_provider
from apps.knowledge_base.chunking import build_chunks

from .match_prompts import ASSESS_SYSTEM, EXTRACT_SYSTEM, assess_prompt, extract_prompt
from .match_schemas import AssessmentList, RequirementList
from .models import EmployerProfile, JobMatchRequest, ProfileAccessEvent
from .public import ip_hash
from .services import ALL_SOURCE_TYPES, EmployerProfileService

logger = logging.getLogger(__name__)

Status = JobMatchRequest.Status
Source = JobMatchRequest.Source

MIN_JD_CHARS = 200
MAX_JD_CHARS = 15_000
MAX_REQUIREMENTS = 25
EVIDENCE_PER_REQUIREMENT = 4
WEIGHT = {"required": 2, "preferred": 1}
CREDIT = {"met": 1.0, "partial": 0.5, "no_evidence": 0.0}
NOT_FOUND = "Not found in the candidate's profile."
DISCLAIMER = (
    "This score is an aid based only on the information in the candidate's profile. "
    "It is not a hiring decision, and a missing item may simply not be in the profile."
)
FAILURE_MESSAGE = "The job description couldn't be analysed right now. Please try again."


class MatchError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def jd_hash(job_description: str) -> str:
    normalised = re.sub(r"\s+", " ", job_description.strip().lower())
    return hashlib.sha256(normalised.encode()).hexdigest()


def source_types_for(profile: EmployerProfile, source: str) -> list[str]:
    # A self-check is private, so it may use everything; employers see only visible sections.
    return ALL_SOURCE_TYPES if source == Source.CANDIDATE_SELF else EmployerProfileService.visible_source_types(profile)


def fingerprint(profile: EmployerProfile, source: str) -> str:
    allowed = set(source_types_for(profile, source))
    parts = sorted(f"{c.key}:{c.content_hash}" for c in build_chunks(profile.user) if c.source_type in allowed)
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def score(requirements: list[dict]) -> int | None:
    possible = sum(WEIGHT[r["importance"]] for r in requirements)
    if not possible:
        return None
    earned = sum(WEIGHT[r["importance"]] * CREDIT[r["status"]] for r in requirements)
    return round(100 * earned / possible)


def summarise(requirements: list[dict]) -> dict:
    return {
        "strengths": [r["text"] for r in requirements if r["status"] == "met"],
        "gaps": [r["text"] for r in requirements if r["status"] == "no_evidence" and r["importance"] == "required"],
    }


class JobMatchService:
    @staticmethod
    @transaction.atomic
    def request(profile: EmployerProfile, job_description: str, *, source: str, request=None) -> JobMatchRequest:
        """Validate, reuse a cached report if one applies, or queue a new match."""
        from .tasks import run_job_match

        text = (job_description or "").strip()
        if len(text) < MIN_JD_CHARS:
            raise MatchError("too_short", f"Paste the full job description (at least {MIN_JD_CHARS} characters).")
        if len(text) > MAX_JD_CHARS:
            raise MatchError("too_long", f"Job descriptions can be at most {MAX_JD_CHARS:,} characters.")

        if source == Source.EMPLOYER_PROFILE:
            today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if profile.matches.filter(source=source, created_at__gte=today).count() >= settings.MATCH_DAILY_LIMIT_PER_PROFILE:
                raise MatchError("daily_limit", "Job matching is unavailable for the rest of today.", status=429)
            if request is not None:
                EmployerProfileService.log_event(profile, ProfileAccessEvent.Kind.MATCH, request)

        digest, fp = jd_hash(text), fingerprint(profile, source)
        match = JobMatchRequest.objects.create(
            profile=profile,
            source=source,
            jd_hash=digest,
            profile_fingerprint=fp,
            ip_hash=ip_hash(request) if request is not None else "",
        )
        cached = (
            JobMatchRequest.objects.filter(
                profile=profile, jd_hash=digest, profile_fingerprint=fp, status=Status.DONE
            )
            .exclude(pk=match.pk)
            .first()
        )
        if cached is not None:
            for field in ("job_title", "requirements", "score", "summary", "model"):
                setattr(match, field, getattr(cached, field))
            match.status, match.completed_at = Status.DONE, timezone.now()
            match.save()
            return match

        # argsrepr keeps the job description out of Celery's logs and monitoring events.
        transaction.on_commit(
            lambda: run_job_match.apply_async(args=(match.pk, text), argsrepr=f"({match.pk}, '<job description>')")
        )
        return match

    @staticmethod
    def run(match_id: int, job_description: str) -> None:
        """Analyse one job description. Raises AITransientError for the task to retry."""
        with transaction.atomic():
            match = JobMatchRequest.objects.select_for_update().select_related("profile__user").get(pk=match_id)
            if match.status not in (Status.PENDING, Status.RUNNING):
                return
            match.status = Status.RUNNING
            match.save(update_fields=["status"])

        provider = get_provider(settings.CHAT_MODEL)
        extracted = provider.generate_structured(
            system=EXTRACT_SYSTEM, prompt=extract_prompt(job_description), schema=RequirementList
        ).output
        requirements = [r for r in extracted.requirements if r.text.strip()][:MAX_REQUIREMENTS]

        if not requirements:
            JobMatchService._finish(match, extracted.job_title, [], provider)
            return

        evidence = EmployerProfileService.evidence(
            match.profile,
            [r.text for r in requirements],
            source_types=source_types_for(match.profile, match.source),
            k=EVIDENCE_PER_REQUIREMENT,
        )
        by_key = {c.key: c for c in evidence}
        assessed = provider.generate_structured(
            system=ASSESS_SYSTEM, prompt=assess_prompt(requirements, evidence), schema=AssessmentList
        ).output
        by_index = {a.index: a for a in assessed.assessments}

        results = []
        for i, req in enumerate(requirements):
            a = by_index.get(i)
            cited = [by_key[ref] for ref in dict.fromkeys(a.evidence_refs if a else []) if ref in by_key]
            status = a.status if a else "no_evidence"
            if status != "no_evidence" and not cited:
                status = "no_evidence"  # a verdict without evidence doesn't count
            results.append(
                {
                    "text": req.text.strip()[:500],
                    "importance": req.importance,
                    "status": status,
                    "evidence": [
                        {"source_type": c.source_type, "source_id": c.source_id, "label": c.text.split("\n", 1)[0][:200]}
                        for c in cited
                    ]
                    if status != "no_evidence"
                    else [],
                    "explanation": (a.explanation.strip()[:500] if a and status != "no_evidence" else NOT_FOUND),
                }
            )
        JobMatchService._finish(match, extracted.job_title, results, provider)

    @staticmethod
    def _finish(match, job_title, results, provider) -> None:
        match.job_title = (job_title or "").strip()[:200]
        match.requirements = results
        match.score = score(results)
        match.summary = summarise(results)
        match.model = getattr(provider, "model", "")
        match.status = Status.DONE
        match.completed_at = timezone.now()
        match.save()
        logger.info("Job match %s done: %s requirements, score %s", match.pk, len(results), match.score)

    @staticmethod
    def mark_failed(match_id: int, code: str) -> None:
        JobMatchRequest.objects.filter(pk=match_id, status__in=[Status.PENDING, Status.RUNNING]).update(
            status=Status.FAILED, error_code=code, error_message=FAILURE_MESSAGE, completed_at=timezone.now()
        )

