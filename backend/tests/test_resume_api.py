import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.documents.models import CandidateDocument
from apps.resume_parser.models import ResumeParseJob

from .files import blank_pdf, text_docx, text_pdf

UPLOAD_URL = "/api/resumes/"


def upload(api, data, name="resume.pdf", content_type="application/pdf"):
    return api.post(UPLOAD_URL, {"file": SimpleUploadedFile(name, data, content_type=content_type)}, format="multipart")


@pytest.mark.parametrize(
    ("data", "name"),
    [(text_pdf(), "resume.pdf"), (text_docx(), "resume.docx")],
)
def test_upload_parses_in_background(api, fake_provider, django_capture_on_commit_callbacks, data, name):
    with django_capture_on_commit_callbacks(execute=True):
        response = upload(api, data, name=name, content_type="application/octet-stream")

    assert response.status_code == 201
    job_id = response.json()["id"]
    assert response.json()["status"] == "pending"

    detail = api.get(f"/api/resumes/jobs/{job_id}/").json()
    assert detail["status"] == "ready_for_review"
    assert detail["document"]["original_filename"] == name

    document = CandidateDocument.objects.get()
    assert "Acme Corp" in document.extracted_text
    assert name not in document.file.name  # stored under an opaque key


def test_upload_rejects_scanned_pdf(api):
    response = upload(api, blank_pdf())
    assert response.status_code == 400
    assert response.json()["code"] == "no_text"
    assert not CandidateDocument.objects.exists()
    assert not ResumeParseJob.objects.exists()


def test_upload_rejects_disguised_file(api):
    response = upload(api, b"MZ\x90\x00 definitely not a resume", name="resume.pdf")
    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_type"


def test_upload_rejects_oversized_file(api, settings):
    settings.RESUME_MAX_UPLOAD_MB = 0
    response = upload(api, text_pdf())
    assert response.status_code == 400
    assert response.json()["code"] == "too_large"


@pytest.mark.django_db
def test_endpoints_require_authentication():
    client = APIClient()
    assert upload(client, text_pdf()).status_code == 403
    assert client.get("/api/resumes/jobs/1/").status_code == 403
    assert client.get("/api/resumes/jobs/latest/").status_code == 403


def test_other_users_jobs_are_not_found(api, make_user, fake_provider, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        job_id = upload(api, text_pdf()).json()["id"]
    ResumeParseJob.objects.filter(pk=job_id).update(status=ResumeParseJob.Status.FAILED)

    intruder = APIClient()
    intruder.force_authenticate(make_user("mallory@example.com"))
    assert intruder.get(f"/api/resumes/jobs/{job_id}/").status_code == 404
    assert intruder.post(f"/api/resumes/jobs/{job_id}/retry/").status_code == 404
    assert intruder.get("/api/resumes/jobs/latest/").status_code == 404


def test_latest_job_and_dashboard(api, fake_provider, django_capture_on_commit_callbacks):
    assert api.get("/api/resumes/jobs/latest/").status_code == 404

    with django_capture_on_commit_callbacks(execute=True):
        job_id = upload(api, text_pdf()).json()["id"]

    assert api.get("/api/resumes/jobs/latest/").json()["id"] == job_id
    dashboard = api.get("/api/me/").json()["dashboard"]
    assert dashboard["has_resume"] is True
    assert dashboard["latest_parse_status"] == "ready_for_review"
    assert dashboard["latest_job_id"] == job_id


def test_retry_only_for_failed_jobs(api, fake_provider, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        job_id = upload(api, text_pdf()).json()["id"]
    assert api.post(f"/api/resumes/jobs/{job_id}/retry/").status_code == 409

    ResumeParseJob.objects.filter(pk=job_id).update(status=ResumeParseJob.Status.FAILED, error_code="ai_error")
    with django_capture_on_commit_callbacks(execute=True):
        response = api.post(f"/api/resumes/jobs/{job_id}/retry/")
    assert response.status_code == 200
    assert api.get(f"/api/resumes/jobs/{job_id}/").json()["status"] == "ready_for_review"
