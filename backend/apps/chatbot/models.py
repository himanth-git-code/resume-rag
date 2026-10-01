"""Employer chat sessions on a candidate's AI profile (SPEC §10), kept for the candidate to review."""

import secrets

from django.db import models


def new_session_id() -> str:
    return secrets.token_urlsafe(16)


class EmployerChatSession(models.Model):
    profile = models.ForeignKey("ai_profile.EmployerProfile", on_delete=models.CASCADE, related_name="chat_sessions")
    # Random id held by the employer's browser; never a sequential pk.
    public_id = models.CharField(max_length=32, unique=True, default=new_session_id)
    ip_hash = models.CharField(max_length=64)
    question_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_activity", "-pk"]


class EmployerChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Employer"
        ASSISTANT = "assistant", "Assistant"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    class AnswerStatus(models.TextChoices):
        ANSWERED = "answered", "Answered"
        NOT_FOUND = "not_found", "Not in profile"
        DECLINED = "declined", "Declined"

    session = models.ForeignKey(EmployerChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DONE)
    answer_status = models.CharField(max_length=10, choices=AnswerStatus.choices, blank=True)
    # [{"source_type", "source_id", "label"}]: profile items the answer is grounded in.
    citations = models.JSONField(default=list, blank=True)
    model = models.CharField(max_length=100, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "pk"]
