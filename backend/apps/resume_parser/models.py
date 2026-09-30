from django.db import models


class ResumeParseJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PARSING = "parsing", "Parsing"
        READY_FOR_REVIEW = "ready_for_review", "Ready for review"
        APPLIED = "applied", "Applied"
        FAILED = "failed", "Failed"

    document = models.ForeignKey("documents.CandidateDocument", on_delete=models.CASCADE, related_name="parse_jobs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    # AI draft (ResumeExtraction as JSON). Only the candidate's save copies it to the profile.
    result = models.JSONField(null=True, blank=True)
    model = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=50, blank=True)
    # Safe to show the candidate: never a stack trace or vendor message.
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ResumeParseJob #{self.pk} ({self.status})"
