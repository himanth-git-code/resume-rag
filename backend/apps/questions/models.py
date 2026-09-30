"""Interview questions generated from a candidate's approved profile and notes (SPEC §8)."""

from django.conf import settings
from django.db import models


class QuestionGeneration(models.Model):
    class Kind(models.TextChoices):
        FULL = "full", "Full set"
        MORE = "more", "More questions"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_generations")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    # For "more": {"category": ..., "source": "experience:12"} (either may be absent).
    scope = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    # Planned section keys ("overview", "skills", "experience:12", ...) and those finished so far.
    sections = models.JSONField(default=list)
    completed_sections = models.JSONField(default=list)
    # Fingerprint of the profile + notes the questions were generated from.
    source_hash = models.CharField(max_length=64, blank=True)
    model = models.CharField(max_length=100, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]


class Question(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General"
        TECHNICAL = "technical", "Technical"
        EXPERIENCE = "experience", "Experience"
        PROJECT = "project", "Project"
        BEHAVIORAL = "behavioral", "Behavioral"
        DOMAIN = "domain", "Domain"

    class Difficulty(models.TextChoices):
        FOUNDATIONAL = "foundational", "Foundational"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questions")
    generation = models.ForeignKey(QuestionGeneration, on_delete=models.CASCADE, related_name="questions")
    # Deep-dive follow-ups point at the question they follow.
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="follow_ups")
    # Only active questions are shown; a regeneration stays inactive until it has fully succeeded.
    is_active = models.BooleanField(default=True)
    section = models.CharField(max_length=50)
    category = models.CharField(max_length=20, choices=Category.choices)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices)
    topic = models.CharField(max_length=200, blank=True)
    text = models.TextField()
    # Profile items the question is about, as refs ("experience:12", "skill:4", ...), for filtering.
    source_refs = models.JSONField(default=list)
    # [{"ref", "label", "text"}]: which of the candidate's own items to draw on. Never invented facts.
    talking_points = models.JSONField(default=list)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "pk"]
        indexes = [models.Index(fields=["owner", "is_active", "category"])]
