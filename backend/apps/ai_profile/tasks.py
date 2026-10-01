from celery import shared_task

from apps.ai.errors import AIError, AITransientError

from .matching import JobMatchService


@shared_task(
    bind=True,
    autoretry_for=(AITransientError,),
    retry_backoff=10,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
)
def run_job_match(self, match_id: int, job_description: str) -> None:
    # The job description travels only in the task message; it is never stored or logged.
    try:
        JobMatchService.run(match_id, job_description)
    except AITransientError:
        if self.request.retries >= self.max_retries:
            JobMatchService.mark_failed(match_id, "ai_unavailable")
            return
        raise
    except AIError:
        JobMatchService.mark_failed(match_id, "ai_error")
    except Exception:
        # Never leave a report stuck "analysing"; the error is still raised for logging.
        JobMatchService.mark_failed(match_id, "error")
        raise
