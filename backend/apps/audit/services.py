import logging

from django.db import transaction

from .models import AuditLog

logger = logging.getLogger(__name__)

ActorType = AuditLog.ActorType
# Keys that must never be stored, whatever a caller passes.
FORBIDDEN_KEYS = {"body", "text", "content", "message", "job_description", "resume", "password", "description"}


class AuditService:
    @staticmethod
    def record(action: str, *, actor=None, request=None, subject_user=None, target=None, actor_type=None, **metadata) -> None:
        """Write one audit event. Best-effort: never raises into the caller's flow.

        `target` may be a model instance (type and pk are recorded). Metadata
        must be small and never contain user content (enforced by key name).
        """
        try:
            from apps.ai_profile.public import ip_hash

            if actor_type is None:
                if actor is None:
                    actor_type = ActorType.SYSTEM if request is None else ActorType.VISITOR
                else:
                    actor_type = ActorType.ADMIN if getattr(actor, "is_staff", False) else ActorType.USER
            clean = {k: v for k, v in metadata.items() if k not in FORBIDDEN_KEYS and v is not None}
            with transaction.atomic():  # savepoint: a failure here can't poison the caller's transaction
                AuditLog.objects.create(
                    actor=actor if getattr(actor, "pk", None) else None,
                    actor_type=actor_type,
                    action=action[:60],
                    target_type=target._meta.model_name if target is not None else "",
                    target_id=str(target.pk) if target is not None else "",
                    subject_user=subject_user if getattr(subject_user, "pk", None) else None,
                    metadata=clean,
                    ip_hash=ip_hash(request) if request is not None else "",
                )
        except Exception:
            logger.exception("Audit write failed for %s", action)


def record(action: str, **kwargs) -> None:
    AuditService.record(action, **kwargs)
