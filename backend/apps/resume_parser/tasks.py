from celery import shared_task

from apps.ai.errors import AITransientError

from .services import ResumeProcessingService


@shared_task(
    bind=True,
    autoretry_for=(AITransientError,),
    retry_backoff=30,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def process_resume(self, job_id: int) -> None:
    try:
        ResumeProcessingService.run(job_id)
    except AITransientError:
        if self.request.retries >= self.max_retries:
            ResumeProcessingService.mark_failed(job_id, "ai_unavailable")
            return
        raise
