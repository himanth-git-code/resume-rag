from celery import shared_task

from apps.ai.errors import AITransientError

from .services import EmployerChatService


@shared_task(
    bind=True,
    autoretry_for=(AITransientError,),
    retry_backoff=5,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def answer_message(self, message_id: int) -> None:
    try:
        EmployerChatService.answer(message_id)
    except AITransientError:
        if self.request.retries >= self.max_retries:
            EmployerChatService.mark_failed(message_id, "ai_unavailable")
            return
        raise
    except Exception:
        # Never leave the employer waiting on a reply that will not come.
        EmployerChatService.mark_failed(message_id, "error")
        raise
