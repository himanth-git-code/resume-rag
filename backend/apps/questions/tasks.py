from celery import shared_task

from apps.ai.errors import AIError, AITransientError

from .services import QuestionGenerationService


@shared_task(
    bind=True,
    autoretry_for=(AITransientError,),
    retry_backoff=30,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def generate_questions(self, generation_id: int) -> None:
    try:
        QuestionGenerationService.run(generation_id)
    except AITransientError:
        if self.request.retries >= self.max_retries:
            QuestionGenerationService.mark_failed(generation_id, "ai_unavailable")
            return
        raise
    except AIError:
        QuestionGenerationService.mark_failed(generation_id, "ai_error")
