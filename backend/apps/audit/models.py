"""Audit trail of important events (SPEC §16). Metadata never holds user content."""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class ActorType(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"
        SYSTEM = "system", "System"
        VISITOR = "visitor", "Visitor"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    actor_type = models.CharField(max_length=10, choices=ActorType.choices)
    # Dotted code, e.g. "auth.login", "resume.uploaded", "admin.user_suspended".
    action = models.CharField(max_length=60)
    target_type = models.CharField(max_length=40, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    # The candidate this event concerns, for per-user history.
    subject_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events"
    )
    metadata = models.JSONField(default=dict, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["subject_user", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]
