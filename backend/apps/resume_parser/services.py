import logging

from django.db import transaction
from django.utils import timezone

from apps.ai.errors import AIOutputError, AIPermanentError, AITransientError
from apps.ai.providers import get_provider
from apps.documents.services import DocumentService

from .models import ResumeParseJob
from .prompts import RESUME_EXTRACTION_SYSTEM, resume_extraction_prompt
from .schemas import ResumeExtraction

logger = logging.getLogger(__name__)

Status = ResumeParseJob.Status

FAILURE_MESSAGES = {
    "refusal": "We couldn't process this resume automatically. Please try again, or enter your details manually.",
    "max_tokens": "This resume is too long to process in one go. Try a shorter version.",
    "ai_unavailable": "The parsing service is busy right now. Please try again in a few minutes.",
    "ai_error": "Something went wrong while reading your resume. Please try again.",
}


class ResumeProcessingService:
    @staticmethod
    def create_job(owner, upload) -> ResumeParseJob:
        """Store the upload and queue parsing. Raises DocumentRejected for unusable files."""
        from .tasks import process_resume

        with transaction.atomic():
            document = DocumentService.create_resume(owner, upload)
            job = ResumeParseJob.objects.create(document=document)
            transaction.on_commit(lambda: process_resume.delay(job.pk))
        return job

    @staticmethod
    def retry(job: ResumeParseJob) -> ResumeParseJob:
        from .tasks import process_resume

        with transaction.atomic():
            job = ResumeParseJob.objects.select_for_update().get(pk=job.pk)
            if job.status != Status.FAILED:
                return job
            job.status = Status.PENDING
            job.error_code = job.error_message = ""
            job.save(update_fields=["status", "error_code", "error_message", "updated_at"])
            transaction.on_commit(lambda: process_resume.delay(job.pk))
        return job

    @staticmethod
    def run(job_id: int) -> None:
        """Parse one job. Idempotent: a job that's already past parsing is left alone.

        Raises AITransientError so the task can retry; permanent failures are
        recorded on the job. Never writes to the candidate's profile.
        """
        with transaction.atomic():
            job = ResumeParseJob.objects.select_for_update().select_related("document").get(pk=job_id)
            if job.status not in (Status.PENDING, Status.PARSING):
                return
            job.status = Status.PARSING
            job.attempts += 1
            job.save(update_fields=["status", "attempts", "updated_at"])

        text = job.document.extracted_text
        try:
            result = get_provider().generate_structured(
                system=RESUME_EXTRACTION_SYSTEM,
                prompt=resume_extraction_prompt(text),
                schema=ResumeExtraction,
            )
        except AITransientError:
            logger.warning("Resume parse job %s: transient AI error (attempt %s)", job.pk, job.attempts)
            raise
        except AIOutputError as exc:
            logger.warning("Resume parse job %s: unusable AI output (%s)", job.pk, exc.reason)
            ResumeProcessingService.mark_failed(job.pk, exc.reason if exc.reason in FAILURE_MESSAGES else "ai_error")
            return
        except AIPermanentError:
            logger.exception("Resume parse job %s: AI call failed", job.pk)
            ResumeProcessingService.mark_failed(job.pk, "ai_error")
            return

        ResumeParseJob.objects.filter(pk=job.pk, status=Status.PARSING).update(
            status=Status.READY_FOR_REVIEW,
            result=result.output.model_dump(mode="json"),
            model=result.model,
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )

    @staticmethod
    def mark_failed(job_id: int, code: str) -> None:
        ResumeParseJob.objects.filter(pk=job_id).exclude(status__in=[Status.READY_FOR_REVIEW, Status.APPLIED]).update(
            status=Status.FAILED,
            error_code=code,
            error_message=FAILURE_MESSAGES.get(code, FAILURE_MESSAGES["ai_error"]),
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )

    @staticmethod
    def latest_job_for(owner) -> ResumeParseJob | None:
        return ResumeParseJob.objects.filter(document__owner=owner).select_related("document").first()

    @staticmethod
    def get_job_for(owner, job_id: int) -> ResumeParseJob:
        """Raises ResumeParseJob.DoesNotExist for other users' jobs, just as for missing ones."""
        return ResumeParseJob.objects.select_related("document").get(pk=job_id, document__owner=owner)
