"""Employer-facing AI profile: a secret link to a candidate's chosen profile sections (SPEC §9)."""

import secrets

from django.conf import settings
from django.db import models

SECTIONS = ("summary", "experience", "projects", "skills", "education", "certifications", "achievements", "links", "contact", "notes")
# Contact details and private notes are opt-in; everything else is shown by default.
DEFAULT_VISIBLE = {section: section not in ("contact", "notes") for section in SECTIONS}


def default_visible_sections():
    return dict(DEFAULT_VISIBLE)


def new_token() -> str:
    return secrets.token_urlsafe(32)


class EmployerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employer_profile")
    enabled = models.BooleanField(default=False)
    token = models.CharField(max_length=64, unique=True, default=new_token)
    token_created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    visible_sections = models.JSONField(default=default_visible_sections)
    chatbot_enabled = models.BooleanField(default=True)
    matching_enabled = models.BooleanField(default=True)
    # Set by an administrator (e.g. abuse); the candidate can't override it.
    admin_disabled = models.BooleanField(default=False)
    admin_disabled_reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_visible(self, section: str) -> bool:
        return bool({**DEFAULT_VISIBLE, **(self.visible_sections or {})}.get(section))

    def __str__(self):
        return f"Employer profile of {self.user}"


class ProfileAccessEvent(models.Model):
    class Kind(models.TextChoices):
        VIEW = "view", "Profile viewed"
        CHAT_SESSION = "chat_session", "Chat started"
        MATCH = "match", "Job match requested"

    profile = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="access_events")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    # Salted hash, never the raw IP.
    ip_hash = models.CharField(max_length=64)
    user_agent = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]


def new_match_id() -> str:
    return secrets.token_urlsafe(16)


class JobMatchRequest(models.Model):
    """A job description matched against a candidate's profile (SPEC §10A).

    The job description itself is never stored: only its hash (for caching).
    """

    class Source(models.TextChoices):
        EMPLOYER_PROFILE = "employer_profile", "Employer"
        WEBSITE = "website", "Website visitor"
        CANDIDATE_SELF = "candidate_self", "Self-check"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    profile = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="matches")
    public_id = models.CharField(max_length=32, unique=True, default=new_match_id)
    source = models.CharField(max_length=20, choices=Source.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    jd_hash = models.CharField(max_length=64)
    # Source types the match may use when they differ from the employer profile's (website matches).
    source_types = models.JSONField(null=True, blank=True)
    # Fingerprint of the profile data the match may use; a change invalidates cached reports.
    profile_fingerprint = models.CharField(max_length=64)
    ip_hash = models.CharField(max_length=64, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    # [{"text", "importance", "status", "evidence": [{source_type, source_id, label}], "explanation"}]
    requirements = models.JSONField(default=list, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)  # {"strengths": [...], "gaps": [...]}
    model = models.CharField(max_length=100, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["profile", "jd_hash", "profile_fingerprint"])]
