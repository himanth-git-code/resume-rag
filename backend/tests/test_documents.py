import io
import zipfile

import pytest

from apps.documents.extraction import DocumentRejected, detect_content_type, extract_text
from apps.documents.models import CandidateDocument

from .files import blank_pdf, text_docx, text_pdf


def test_detects_pdf_and_docx_by_content():
    assert detect_content_type(text_pdf()) == CandidateDocument.ContentType.PDF
    assert detect_content_type(text_docx()) == CandidateDocument.ContentType.DOCX


@pytest.mark.parametrize("data", [b"hello world", b"\x89PNG\r\n\x1a\n...", b""])
def test_rejects_unsupported_content(data):
    with pytest.raises(DocumentRejected) as exc:
        detect_content_type(data)
    assert exc.value.code == "unsupported_type"


def test_rejects_zip_that_is_not_docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("notes.txt", "x")
    with pytest.raises(DocumentRejected) as exc:
        detect_content_type(buf.getvalue())
    assert exc.value.code == "unsupported_type"


def test_extracts_pdf_text():
    text = extract_text(text_pdf(), CandidateDocument.ContentType.PDF, max_pdf_pages=20)
    assert "Acme Corp" in text
    assert "Redis caching" in text


def test_extracts_docx_paragraphs_and_tables():
    text = extract_text(text_docx(), CandidateDocument.ContentType.DOCX, max_pdf_pages=20)
    assert "Acme Corp" in text
    assert "Kubernetes" in text  # from the table


def test_rejects_pdf_without_text_layer():
    with pytest.raises(DocumentRejected) as exc:
        extract_text(blank_pdf(), CandidateDocument.ContentType.PDF, max_pdf_pages=20)
    assert exc.value.code == "no_text"
    assert "scanned" in exc.value.message


def test_rejects_pdf_over_page_limit():
    with pytest.raises(DocumentRejected) as exc:
        extract_text(blank_pdf(pages=3), CandidateDocument.ContentType.PDF, max_pdf_pages=2)
    assert exc.value.code == "too_many_pages"


def test_rejects_corrupt_pdf():
    with pytest.raises(DocumentRejected) as exc:
        extract_text(b"%PDF-1.4\nnot really a pdf", CandidateDocument.ContentType.PDF, max_pdf_pages=20)
    assert exc.value.code in {"unreadable", "no_text"}
