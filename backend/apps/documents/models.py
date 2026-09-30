import uuid

from django.conf import settings
from django.db import models


def document_upload_to(instance, filename):
    # Opaque key: never the user's filename, which may contain personal data.
    ext = {"application/pdf": "pdf", DOCX_CONTENT_TYPE: "docx"}.get(instance.content_type, "bin")
    return f"documents/{instance.owner_id}/{uuid.uuid4().hex}.{ext}"


DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class CandidateDocument(models.Model):
    class Kind(models.TextChoices):
        RESUME = "resume", "Resume"

    class ContentType(models.TextChoices):
        PDF = "application/pdf", "PDF"
        DOCX = DOCX_CONTENT_TYPE, "DOCX"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.RESUME)
    file = models.FileField(upload_to=document_upload_to, max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, choices=ContentType.choices)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    # Extracted plain text. Sensitive: never log it.
    extracted_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "-created_at"])]

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk}"
