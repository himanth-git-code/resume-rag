from unittest import mock

import pytest
from celery.exceptions import Retry
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.ai.errors import AIOutputError, AIPermanentError, AITransientError
from apps.resume_parser.models import ResumeParseJob
from apps.resume_parser.schemas import Experience, ResumeExtraction
from apps.resume_parser.services import ResumeProcessingService
from apps.resume_parser.tasks import process_resume

from .files import text_pdf

Status = ResumeParseJob.Status


@pytest.fixture
def job(user, django_capture_on_commit_callbacks):
    upload = SimpleUploadedFile("resume.pdf", text_pdf(), content_type="application/pdf")
    # Don't run the queued task here; each test drives processing itself.
    with mock.patch("apps.resume_parser.tasks.process_resume.delay"):
        with django_capture_on_commit_callbacks(execute=True):
            return ResumeProcessingService.create_job(user, upload)


def test_run_stores_draft_for_review(job, fake_provider):
    fake_provider.canned[ResumeExtraction] = ResumeExtraction(
        full_name="Jane Doe", experience=[Experience(company="Acme Corp", title="Senior Backend Engineer")]
    )

    ResumeProcessingService.run(job.pk)

    job.refresh_from_db()
    assert job.status == Status.READY_FOR_REVIEW
    assert job.result["full_name"] == "Jane Doe"
    assert job.result["experience"][0]["company"] == "Acme Corp"
    assert job.result["headline"] is None  # missing data stays missing
    assert job.model == "fake"
    assert job.attempts == 1
    # The resume text was sent inside the data delimiters.
    assert "<resume>" in fake_provider.calls[0]["prompt"]
    assert "Acme Corp" in fake_provider.calls[0]["prompt"]


def test_run_is_idempotent_once_ready(job, fake_provider):
    ResumeProcessingService.run(job.pk)
    ResumeProcessingService.run(job.pk)

    assert len(fake_provider.calls) == 1
    job.refresh_from_db()
    assert job.attempts == 1


def test_transient_error_is_raised_for_retry(job):
    provider = mock.Mock()
    provider.generate_structured.side_effect = AITransientError("RateLimitError")
    with mock.patch("apps.resume_parser.services.get_provider", return_value=provider):
        with pytest.raises(AITransientError):
            ResumeProcessingService.run(job.pk)

    job.refresh_from_db()
    assert job.status == Status.PARSING  # still retryable


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (AIOutputError("declined", reason="refusal"), "refusal"),
        (AIOutputError("truncated", reason="max_tokens"), "max_tokens"),
        (AIOutputError("bad", reason="schema_mismatch"), "ai_error"),
        (AIPermanentError("AuthenticationError (401)"), "ai_error"),
    ],
)
def test_permanent_errors_fail_the_job_with_a_safe_message(job, error, code):
    provider = mock.Mock()
    provider.generate_structured.side_effect = error
    with mock.patch("apps.resume_parser.services.get_provider", return_value=provider):
        ResumeProcessingService.run(job.pk)

    job.refresh_from_db()
    assert job.status == Status.FAILED
    assert job.error_code == code
    assert job.error_message
    assert "401" not in job.error_message and "Error" not in job.error_message
    assert job.result is None


def test_task_gives_up_after_max_retries(job):
    provider = mock.Mock()
    provider.generate_structured.side_effect = AITransientError("OverloadedError")
    with mock.patch("apps.resume_parser.services.get_provider", return_value=provider):
        process_resume.apply(args=[job.pk], retries=process_resume.max_retries)

    job.refresh_from_db()
    assert job.status == Status.FAILED
    assert job.error_code == "ai_unavailable"


def test_task_retries_transient_errors(job):
    provider = mock.Mock()
    provider.generate_structured.side_effect = AITransientError("OverloadedError")
    with mock.patch("apps.resume_parser.services.get_provider", return_value=provider):
        with pytest.raises(Retry):
            process_resume.apply(args=[job.pk])

    job.refresh_from_db()
    assert job.status == Status.PARSING


def test_retry_requeues_only_failed_jobs(job, fake_provider, django_capture_on_commit_callbacks):
    ResumeProcessingService.mark_failed(job.pk, "ai_error")
    job.refresh_from_db()

    with mock.patch("apps.resume_parser.tasks.process_resume.delay") as delay:
        with django_capture_on_commit_callbacks(execute=True):
            ResumeProcessingService.retry(job)
    delay.assert_called_once_with(job.pk)
    job.refresh_from_db()
    assert job.status == Status.PENDING
    assert job.error_code == ""
