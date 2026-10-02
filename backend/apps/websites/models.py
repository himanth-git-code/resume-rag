"""Candidate personal websites (SPEC §11-13): configuration, published snapshots, previews and audit."""

import secrets

from django.conf import settings
from django.db import models

from .catalog import DEFAULT_TEMPLATE, DEFAULT_THEME, default_sections


def _default_theme():
    return dict(DEFAULT_THEME)


def _default_sections():
    return default_sections(DEFAULT_TEMPLATE)


def _default_overrides():
    # featured_*: list of profile item ids to show, or null for all.
    return {"tagline": "", "intro": "", "titles": {}, "featured_projects": None, "featured_achievements": None, "leadership": []}


class Website(models.Model):
    class BioSource(models.TextChoices):
        CANDIDATE = "candidate", "Written by the candidate"
        AI = "ai", "AI draft, approved by the candidate"

    class DraftStatus(models.TextChoices):
        NONE = "", "None"
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="website")
    # Public address /portfolio/<slug>; null until the candidate picks one.
    slug = models.CharField(max_length=40, unique=True, null=True, blank=True)
    template = models.CharField(max_length=20, default=DEFAULT_TEMPLATE)
    theme = models.JSONField(default=_default_theme)
    sections = models.JSONField(default=_default_sections)
    overrides = models.JSONField(default=_default_overrides)
    # The published bio. Only ever text the candidate saved (and so approved, SPEC §23).
    bio_text = models.TextField(blank=True)
    bio_source = models.CharField(max_length=10, choices=BioSource.choices, blank=True)
    bio_approved_at = models.DateTimeField(null=True, blank=True)
    # The latest AI draft, kept separate and never published as-is.
    bio_draft_status = models.CharField(max_length=10, choices=DraftStatus.choices, blank=True)
    bio_draft_text = models.TextField(blank=True)
    bio_draft_requested_at = models.DateTimeField(null=True, blank=True)
    show_chatbot = models.BooleanField(default=True)
    show_matching = models.BooleanField(default=False)
    published_version = models.ForeignKey(
        "WebsiteVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Website of {self.user}"


class WebsiteVersion(models.Model):
    """A frozen copy of the site as published. The live site only ever serves these."""

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    template = models.CharField(max_length=20)
    data = models.JSONField()
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-number"]
        constraints = [models.UniqueConstraint(fields=["website", "number"], name="unique_version_number")]


def new_preview_token() -> str:
    return secrets.token_urlsafe(32)


class PreviewToken(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="preview_tokens")
    token = models.CharField(max_length=64, unique=True, default=new_preview_token)
    expires_at = models.DateTimeField()
    opened_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WebsiteEvent(models.Model):
    class Kind(models.TextChoices):
        PREVIEW_OPENED = "preview_opened", "Preview opened"
        PUBLISHED = "published", "Published"
        UNPUBLISHED = "unpublished", "Unpublished"
        PUBLIC_VIEW = "public_view", "Public view"

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    ip_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
