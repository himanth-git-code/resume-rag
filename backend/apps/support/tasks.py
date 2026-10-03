from celery import shared_task

from .notifications import send_for_message


@shared_task(bind=True, max_retries=5, retry_backoff=60, retry_backoff_max=1800, autoretry_for=(OSError,))
def send_support_email(self, message_id: int) -> str:
    # emailed_at makes this idempotent: a retried task never sends twice.
    return send_for_message(message_id)
