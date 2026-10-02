from celery import shared_task

from apps.ai.errors import AITransientError

from .bio import BioService


@shared_task(
    bind=True,
    autoretry_for=(AITransientError,),
    retry_backoff=10,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
)
def draft_bio(self, website_id: int, person: str) -> None:
    try:
        BioService.run(website_id, person)
    except AITransientError:
        if self.request.retries >= self.max_retries:
            BioService.mark_failed(website_id)
            return
        raise
    except Exception:
        # Any other failure ends the draft so the editor isn't left waiting.
        BioService.mark_failed(website_id)
        raise
