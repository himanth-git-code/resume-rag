"""The candidate's structured profile: the source of truth for the knowledge base.

Rows are only ever written by CandidateProfileService.save, i.e. when the
candidate saves the review form. Field names mirror
apps.resume_parser.schemas.ResumeExtraction so a reviewed draft maps 1:1.
Dates are kept as the candidate wrote them ("Jan 2020", "Present").
"""

from django.conf import settings
from django.db import models


class SourceType(models.TextChoices):
    RESUME = "resume", "Resume"
    CANDIDATE_INPUT = "candidate_input", "Candidate input"


class CandidateProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_profile")
    full_name = models.CharField(max_length=200, blank=True)
    headline = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    email = models.CharField(max_length=254, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)
    # The resume the profile was last reviewed from, for provenance of resume-sourced rows.
    source_document = models.ForeignKey(
        "documents.CandidateDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user}"


class ProfileItem(models.Model):
    """Common fields for the repeatable sections of a profile."""

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="%(class)ss")
    order = models.PositiveSmallIntegerField(default=0)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.CANDIDATE_INPUT)
    source_document = models.ForeignKey(
        "documents.CandidateDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class CandidateLink(ProfileItem):
    label = models.CharField(max_length=100, blank=True)
    url = models.CharField(max_length=500)


class CandidateSkill(ProfileItem):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, blank=True)


class CandidateExperience(ProfileItem):
    company = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.CharField(max_length=50, blank=True)
    end_date = models.CharField(max_length=50, blank=True)
    is_current = models.BooleanField(null=True, blank=True)
    description = models.TextField(blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    achievements = models.JSONField(default=list, blank=True)
    technologies = models.JSONField(default=list, blank=True)


class CandidateEducation(ProfileItem):
    institution = models.CharField(max_length=200, blank=True)
    degree = models.CharField(max_length=200, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    start_date = models.CharField(max_length=50, blank=True)
    end_date = models.CharField(max_length=50, blank=True)
    grade = models.CharField(max_length=100, blank=True)


class CandidateCertification(ProfileItem):
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200, blank=True)
    issue_date = models.CharField(max_length=50, blank=True)
    expiry_date = models.CharField(max_length=50, blank=True)
    credential_id = models.CharField(max_length=200, blank=True)
    url = models.CharField(max_length=500, blank=True)


class CandidateProject(ProfileItem):
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    technologies = models.JSONField(default=list, blank=True)
    url = models.CharField(max_length=500, blank=True)
    start_date = models.CharField(max_length=50, blank=True)
    end_date = models.CharField(max_length=50, blank=True)


class CandidateAchievement(ProfileItem):
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    date = models.CharField(max_length=50, blank=True)


class CandidateNote(models.Model):
    """Free-text context from the candidate that isn't on the resume (SPEC §2, §7)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_notes")
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return self.title
