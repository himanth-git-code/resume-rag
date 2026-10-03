"""Candidate support tickets (SPEC §15)."""

import uuid

from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING_FOR_USER = "waiting_for_user", "Waiting for user"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    # Human-friendly reference (SUP-000123), set from the pk right after creation.
    number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tickets"
    )
    candidate_last_read_at = models.DateTimeField(null=True, blank=True)
    staff_last_read_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return f"{self.number}: {self.subject}"


class SupportMessage(models.Model):
    class Kind(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        STAFF = "staff", "Support reply"
        INTERNAL = "internal", "Internal note"  # staff only, never shown or emailed to the candidate
        EVENT = "event", "Event"  # e.g. "Status changed to Resolved"

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    body = models.TextField()
    emailed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "pk"]


def attachment_upload_to(instance, filename):
    ext = {"image/png": "png", "image/jpeg": "jpg", "application/pdf": "pdf"}.get(instance.content_type, "bin")
    return f"support/{instance.message.ticket_id}/{uuid.uuid4().hex}.{ext}"


class SupportAttachment(models.Model):
    message = models.ForeignKey(SupportMessage, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_upload_to, max_length=255)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=50)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
