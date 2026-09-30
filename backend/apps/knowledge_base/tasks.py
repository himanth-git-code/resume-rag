from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.ai.errors import AIError, AITransientError

from .models import KnowledgeBaseState
from .services import KnowledgeBaseService

Status = KnowledgeBaseState.Status
LOCK_TIMEOUT = 600


@shared_task(bind=True, max_retries=5)
def rebuild_knowledge_base(self, user_id: int) -> None:
    """Rebuild one candidate's knowledge base.

    A per-user lock serialises rebuilds; if one is already running, this run
    retries shortly after, so the final rebuild always sees the latest data.
    """
    lock = f"kb-rebuild:{user_id}"
    if not cache.add(lock, "1", timeout=LOCK_TIMEOUT):
        raise self.retry(countdown=10)

    try:
        user = get_user_model().objects.filter(pk=user_id).first()
        if user is None:
            return
        KnowledgeBaseService.set_status(user_id, Status.INDEXING)
        KnowledgeBaseService.rebuild(user)
    except AITransientError as exc:
        if self.request.retries >= self.max_retries:
            KnowledgeBaseService.set_status(user_id, Status.FAILED, "ai_unavailable")
            return
        # Stays "indexing" while retrying; existing chunks remain searchable.
        raise self.retry(exc=exc, countdown=min(30 * 2**self.request.retries, 600))
    except AIError:
        KnowledgeBaseService.set_status(user_id, Status.FAILED, "ai_error")
    finally:
        cache.delete(lock)
