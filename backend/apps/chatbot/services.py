import logging

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ai.errors import AIError, AIOutputError, AITransientError
from apps.ai.providers import get_provider
from apps.ai_profile.models import EmployerProfile, ProfileAccessEvent
from apps.ai_profile.public import ip_hash, verify_turnstile
from apps.ai_profile.services import EmployerProfileService
from apps.knowledge_base.chunking import ChunkSpec

from .models import EmployerChatMessage, EmployerChatSession
from .prompts import CHAT_SYSTEM, chat_prompt
from .schemas import ChatAnswer

logger = logging.getLogger(__name__)

Msg = EmployerChatMessage
MAX_QUESTION_CHARS = 1000
MAX_QUESTIONS_PER_SESSION = 20
HISTORY_MESSAGES = 6
# A reply still pending after this long is assumed lost (e.g. the worker died).
STALE_REPLY_AFTER = timedelta(minutes=5)

NOT_FOUND_REPLY = "I don't see that in the candidate's profile."
DECLINED_REPLY = "I can only answer questions about the candidate's professional background."


class ChatError(Exception):
    """A request the public chat must refuse. `code` and `message` are safe to show."""

    status = 400

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _label(chunk: ChunkSpec) -> str:
    return chunk.text.split("\n", 1)[0][:200]


class EmployerChatService:
    @staticmethod
    def evidence(profile: EmployerProfile, question: str) -> list[ChunkSpec]:
        """Visible, approved profile data for `question`. Hidden sections never appear."""
        return EmployerProfileService.evidence(profile, [question])

    @staticmethod
    @transaction.atomic
    def ask(profile: EmployerProfile, *, question: str, session_id: str | None, request, turnstile_token=None):
        """Record an employer question and queue the answer. Returns (session, [user_msg, assistant_msg])."""
        from .tasks import answer_message

        question = (question or "").strip()
        if not question:
            raise ChatError("empty", "Type a question.")
        if len(question) > MAX_QUESTION_CHARS:
            raise ChatError("too_long", f"Keep questions under {MAX_QUESTION_CHARS} characters.")

        if session_id:
            session = (
                EmployerChatSession.objects.select_for_update().filter(profile=profile, public_id=session_id).first()
            )
            if session is None:
                raise ChatError("no_session", "This conversation has ended. Start a new one.", status=404)
        else:
            if not verify_turnstile(turnstile_token, request):
                raise ChatError("bot_check", "Please complete the verification and try again.", status=403)
            session = EmployerChatSession.objects.create(profile=profile, ip_hash=ip_hash(request))
            EmployerProfileService.log_event(profile, ProfileAccessEvent.Kind.CHAT_SESSION, request)

        if session.question_count >= MAX_QUESTIONS_PER_SESSION:
            raise ChatError("session_limit", "This conversation has reached its limit. Start a new one.", status=429)
        # A lost reply mustn't lock the conversation forever.
        session.messages.filter(status=Msg.Status.PENDING, created_at__lt=timezone.now() - STALE_REPLY_AFTER).update(
            status=Msg.Status.FAILED, error_code="stale"
        )
        if session.messages.filter(status=Msg.Status.PENDING).exists():
            raise ChatError("busy", "Please wait for the current answer.", status=409)
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        asked_today = Msg.objects.filter(
            session__profile=profile, role=Msg.Role.USER, created_at__gte=today
        ).count()
        if asked_today >= settings.CHAT_DAILY_LIMIT_PER_PROFILE:
            raise ChatError("daily_limit", "The assistant is unavailable for the rest of today.", status=429)

        user_msg = Msg.objects.create(session=session, role=Msg.Role.USER, content=question)
        reply = Msg.objects.create(session=session, role=Msg.Role.ASSISTANT, status=Msg.Status.PENDING)
        session.question_count += 1
        session.save(update_fields=["question_count", "last_activity"])
        transaction.on_commit(lambda: answer_message.delay(reply.pk))
        return session, [user_msg, reply]

    @staticmethod
    def answer(message_id: int) -> None:
        """Produce a grounded answer for a pending assistant message. Idempotent.

        Raises AITransientError for the task to retry.
        """
        reply = Msg.objects.select_related("session__profile__user").filter(pk=message_id).first()
        if reply is None or reply.status != Msg.Status.PENDING:
            return
        session, profile = reply.session, reply.session.profile

        # The question this reply answers is the latest employer message before it.
        question_msg = session.messages.filter(pk__lt=reply.pk, role=Msg.Role.USER).order_by("-pk").first()
        if question_msg is None:
            EmployerChatService.mark_failed(reply.pk, "no_question")
            return
        history = list(
            reversed(
                session.messages.filter(pk__lt=question_msg.pk, status=Msg.Status.DONE).order_by("-pk")[:HISTORY_MESSAGES]
            )
        )
        previous_question = next((m.content for m in reversed(history) if m.role == Msg.Role.USER), "")

        try:
            # Evidence may call the embeddings service (large profiles), so it shares the AI error handling.
            evidence = EmployerChatService.evidence(profile, f"{previous_question}\n{question_msg.content}".strip())
            result = get_provider(settings.CHAT_MODEL).generate_structured(
                system=CHAT_SYSTEM,
                prompt=chat_prompt(evidence=evidence, history=history, question=question_msg.content),
                schema=ChatAnswer,
            )
        except AITransientError:
            raise
        except AIOutputError as exc:
            logger.info("Chat message %s: model declined or output unusable (%s)", reply.pk, exc.reason)
            EmployerChatService._finish(reply, DECLINED_REPLY, Msg.AnswerStatus.DECLINED, [], "")
            return
        except AIError:
            logger.exception("Chat message %s: AI call failed", reply.pk)
            EmployerChatService.mark_failed(reply.pk, "ai_error")
            return

        by_key = {c.key: c for c in evidence}
        out = result.output
        cited = [by_key[ref] for ref in dict.fromkeys(out.citations) if ref in by_key]
        citations = [{"source_type": c.source_type, "source_id": c.source_id, "label": _label(c)} for c in cited]

        if out.status == "declined":
            text, status = out.answer.strip() or DECLINED_REPLY, Msg.AnswerStatus.DECLINED
            citations = []
        elif out.status == "answered" and citations and out.answer.strip():
            text, status = out.answer.strip(), Msg.AnswerStatus.ANSWERED
        else:
            # Not covered, or an answer that cites nothing: never pass on ungrounded claims.
            text = out.answer.strip() if out.status == "not_found" and out.answer.strip() else NOT_FOUND_REPLY
            status, citations = Msg.AnswerStatus.NOT_FOUND, []
        EmployerChatService._finish(reply, text, status, citations, result.model)

    @staticmethod
    def _finish(reply, text, answer_status, citations, model) -> None:
        Msg.objects.filter(pk=reply.pk, status=Msg.Status.PENDING).update(
            content=text, answer_status=answer_status, citations=citations, model=model, status=Msg.Status.DONE
        )

    @staticmethod
    def mark_failed(message_id: int, code: str) -> None:
        Msg.objects.filter(pk=message_id, status=Msg.Status.PENDING).update(status=Msg.Status.FAILED, error_code=code)

    @staticmethod
    def transcript(session: EmployerChatSession):
        return session.messages.all()
