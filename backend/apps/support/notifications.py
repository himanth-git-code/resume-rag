"""Support emails. Sent from Celery; internal notes are never emailed."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import SupportMessage

logger = logging.getLogger(__name__)
Kind = SupportMessage.Kind
EXCERPT_CHARS = 400


def _support_recipients() -> list[str]:
    configured = [e for e in settings.SUPPORT_NOTIFY_EMAILS if e]
    if configured:
        return configured
    return list(get_user_model().objects.filter(is_staff=True, is_active=True).values_list("email", flat=True))


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= EXCERPT_CHARS else text[: EXCERPT_CHARS - 1] + "…"


def build_email(message: SupportMessage) -> tuple[str, str, list[str]] | None:
    """(subject, body, recipients) for a message, or None if nobody should be emailed."""
    ticket = message.ticket
    base = settings.FRONTEND_URL.rstrip("/")
    if message.kind == Kind.CANDIDATE:
        first = not ticket.messages.filter(pk__lt=message.pk, kind=Kind.CANDIDATE).exists()
        subject = f"[{ticket.number}] {'New request' if first else 'New reply'}: {ticket.subject}"
        body = (
            f"{ticket.candidate.email} {'opened a support request' if first else 'replied'}.\n\n"
            f"{_excerpt(message.body)}\n\nOpen it: {base}/admin/support/{ticket.number}\n"
        )
        return subject, body, _support_recipients()
    if message.kind in (Kind.STAFF, Kind.EVENT):
        subject = f"[{ticket.number}] Update on your support request: {ticket.subject}"
        lead = "Our support team replied:" if message.kind == Kind.STAFF else "Your request was updated:"
        body = f"{lead}\n\n{_excerpt(message.body)}\n\nView the conversation: {base}/support/{ticket.number}\n"
        return subject, body, [ticket.candidate.email]
    return None  # internal notes


def send_for_message(message_id: int) -> str:
    with transaction.atomic():
        message = SupportMessage.objects.select_for_update().select_related("ticket__candidate").filter(pk=message_id).first()
        if message is None or message.emailed_at is not None:
            return "skipped"
        email = build_email(message)
        if email is None or not email[2]:
            return "no_recipients"
        subject, body, recipients = email
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
        message.emailed_at = timezone.now()
        message.save(update_fields=["emailed_at"])
    logger.info("Support email sent for message %s to %s recipient(s)", message_id, len(recipients))
    return "sent"
