import hashlib

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

from .extraction import DocumentRejected, detect_content_type, extract_text
from .models import CandidateDocument


class DocumentService:
    @staticmethod
    def create_resume(owner, upload: UploadedFile) -> CandidateDocument:
        """Validate, extract and store an uploaded resume. Raises DocumentRejected.

        Validation and text extraction are fast and run in the request so the
        candidate gets immediate feedback on unusable files; the slow AI parsing
        runs in a background job.
        """
        max_bytes = settings.RESUME_MAX_UPLOAD_MB * 1024 * 1024
        if upload.size > max_bytes:
            raise DocumentRejected("too_large", f"Files can be at most {settings.RESUME_MAX_UPLOAD_MB} MB.")
        if upload.size == 0:
            raise DocumentRejected("empty", "This file is empty.")

        data = upload.read()
        content_type = detect_content_type(data)
        text = extract_text(data, content_type, max_pdf_pages=settings.RESUME_MAX_PDF_PAGES)

        document = CandidateDocument(
            owner=owner,
            kind=CandidateDocument.Kind.RESUME,
            original_filename=(upload.name or "resume")[:255],
            content_type=content_type,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            extracted_text=text,
        )
        # upload_to derives the key from owner and content_type, so set those first.
        document.file.save("upload", ContentFile(data), save=False)
        document.save()
        return document
