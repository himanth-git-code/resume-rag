from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.candidates.models import CandidateExperience, CandidateProfile, CandidateSkill
from apps.resume_parser.models import ResumeParseJob
from apps.resume_parser.schemas import Experience, ResumeExtraction, Skill
from apps.resume_parser.services import ResumeProcessingService

from .files import text_pdf

Status = ResumeParseJob.Status

DRAFT = ResumeExtraction(
    full_name="Jane Doe",
    email="jane@example.com",
    skills=[Skill(name="Python"), Skill(name="Django", category="Frameworks")],
    experience=[
        Experience(
            company="Acme Corp",
            title="Senior Backend Engineer",
            start_date="Jan 2020",
            end_date="Present",
            is_current=True,
            achievements=["Cut p95 latency by 40%"],
            technologies=["Redis"],
        )
    ],
)


@pytest.fixture
def ready_job(user, fake_provider, django_capture_on_commit_callbacks):
    fake_provider.canned[ResumeExtraction] = DRAFT
    upload = SimpleUploadedFile("resume.pdf", text_pdf(), content_type="application/pdf")
    with django_capture_on_commit_callbacks(execute=True):
        job = ResumeProcessingService.create_job(user, upload)
    job.refresh_from_db()
    assert job.status == Status.READY_FOR_REVIEW
    return job


def profile_payload(**overrides):
    payload = {
        "full_name": "Jane Doe",
        "headline": None,
        "summary": None,
        "email": "jane@example.com",
        "phone": None,
        "location": "Berlin",
        "links": [{"label": "GitHub", "url": "https://github.com/jane", "source_type": "candidate_input"}],
        "skills": [{"name": "Python", "category": None, "source_type": "resume"}],
        "experience": [
            {
                "company": "Acme Corp",
                "title": "Senior Backend Engineer",
                "start_date": "Jan 2020",
                "end_date": "Present",
                "is_current": True,
                "responsibilities": ["Built payment services"],
                "achievements": ["Cut p95 latency by 40%"],
                "technologies": ["Redis", "Django"],
                "source_type": "resume",
            }
        ],
        "education": [],
        "certifications": [],
        "projects": [],
        "achievements": [],
    }
    payload.update(overrides)
    return payload


def test_profile_is_404_until_saved(api):
    assert api.get("/api/profile/").status_code == 404


def test_draft_is_available_once_parsed_and_marks_items_as_resume(api, ready_job):
    response = api.get(f"/api/resumes/jobs/{ready_job.pk}/draft/")

    assert response.status_code == 200
    draft = response.json()
    assert draft["full_name"] == "Jane Doe"
    assert draft["headline"] is None
    assert {s["source_type"] for s in draft["skills"]} == {"resume"}
    assert draft["experience"][0]["company"] == "Acme Corp"


def test_parsing_never_writes_the_profile(ready_job):
    assert not CandidateProfile.objects.exists()


def test_draft_not_available_while_processing(api, user, ready_job):
    ResumeParseJob.objects.filter(pk=ready_job.pk).update(status=Status.PARSING)
    assert api.get(f"/api/resumes/jobs/{ready_job.pk}/draft/").status_code == 409


def test_save_from_draft_applies_job_and_records_provenance(api, ready_job):
    response = api.put("/api/profile/", {**profile_payload(), "job_id": ready_job.pk}, format="json")

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["full_name"] == "Jane Doe"
    assert body["headline"] is None  # missing stays missing
    assert body["experience"][0]["technologies"] == ["Redis", "Django"]

    ready_job.refresh_from_db()
    assert ready_job.status == Status.APPLIED

    profile = CandidateProfile.objects.get()
    assert profile.source_document_id == ready_job.document_id
    skill = CandidateSkill.objects.get()
    assert skill.source_type == "resume" and skill.source_document_id == ready_job.document_id
    link = profile.candidatelinks.get()
    assert link.source_type == "candidate_input" and link.source_document_id is None

    assert api.get("/api/me/").json()["dashboard"]["has_profile"] is True
    assert api.get("/api/profile/").json()["location"] == "Berlin"


def test_saving_replaces_lists_in_order(api):
    api.put("/api/profile/", profile_payload(), format="json")
    skills = [{"name": "Go"}, {"name": "Rust"}, {"name": "SQL"}]
    response = api.put("/api/profile/", profile_payload(skills=skills, experience=[]), format="json")

    assert response.status_code == 200
    assert [s["name"] for s in response.json()["skills"]] == ["Go", "Rust", "SQL"]
    assert not CandidateExperience.objects.exists()
    assert CandidateProfile.objects.count() == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"links": [{"label": "x", "url": "javascript:alert(1)"}]},
        {"experience": [{"description": "no company or title"}]},
        {"skills": [{"name": ""}]},
        {"full_name": "x" * 201},
        {"skills": [{"name": f"s{i}"} for i in range(101)]},
    ],
)
def test_invalid_payload_changes_nothing(api, overrides):
    api.put("/api/profile/", profile_payload(), format="json")

    response = api.put("/api/profile/", profile_payload(**{"full_name": "Changed", **overrides}), format="json")

    assert response.status_code == 400
    assert api.get("/api/profile/").json()["full_name"] == "Jane Doe"


@pytest.mark.parametrize("url", ["https://example.com", "linkedin.com/in/jane", "localhost:3000/cv"])
def test_accepts_http_and_scheme_less_links(api, url):
    response = api.put("/api/profile/", profile_payload(links=[{"url": url}]), format="json")
    assert response.status_code == 200


def test_save_is_atomic(api):
    api.put("/api/profile/", profile_payload(), format="json")

    with mock.patch.object(CandidateExperience.objects, "bulk_create", side_effect=RuntimeError("db down")):
        with pytest.raises(RuntimeError):
            api.put("/api/profile/", profile_payload(full_name="Changed", skills=[]), format="json")

    body = api.get("/api/profile/").json()
    assert body["full_name"] == "Jane Doe"
    assert [s["name"] for s in body["skills"]] == ["Python"]


def test_cannot_apply_a_job_that_is_not_ready(api, ready_job):
    ResumeParseJob.objects.filter(pk=ready_job.pk).update(status=Status.FAILED)
    response = api.put("/api/profile/", {**profile_payload(), "job_id": ready_job.pk}, format="json")
    assert response.status_code == 409
    assert not CandidateProfile.objects.exists()


def test_other_users_cannot_read_or_apply_drafts(ready_job, make_user):
    intruder = APIClient()
    intruder.force_authenticate(make_user("mallory@example.com"))

    assert intruder.get(f"/api/resumes/jobs/{ready_job.pk}/draft/").status_code == 404
    response = intruder.put("/api/profile/", {**profile_payload(), "job_id": ready_job.pk}, format="json")
    assert response.status_code == 404
    assert not CandidateProfile.objects.exists()
    ready_job.refresh_from_db()
    assert ready_job.status == Status.READY_FOR_REVIEW


def test_profiles_are_per_user(api, make_user):
    api.put("/api/profile/", profile_payload(), format="json")

    other = APIClient()
    other.force_authenticate(make_user("bob@example.com"))
    assert other.get("/api/profile/").status_code == 404


@pytest.mark.django_db
def test_profile_requires_authentication():
    client = APIClient()
    assert client.get("/api/profile/").status_code == 403
    assert client.put("/api/profile/", profile_payload(), format="json").status_code == 403


def test_item_ids_are_stable_across_saves(api):
    first = api.put("/api/profile/", profile_payload(), format="json").json()
    role = first["experience"][0]
    skill_id = first["skills"][0]["id"]

    edited_role = {**role, "title": "Staff Engineer"}
    new_skill = {"name": "Go"}
    second = api.put(
        "/api/profile/",
        profile_payload(experience=[edited_role], skills=[new_skill, first["skills"][0]]),
        format="json",
    ).json()

    assert second["experience"][0]["id"] == role["id"]
    assert second["experience"][0]["title"] == "Staff Engineer"
    assert [s["name"] for s in second["skills"]] == ["Go", "Python"]
    assert second["skills"][1]["id"] == skill_id  # kept and reordered
    assert second["skills"][0]["id"] != skill_id


def test_removed_items_are_deleted(api):
    first = api.put("/api/profile/", profile_payload(), format="json").json()
    api.put("/api/profile/", profile_payload(experience=[]), format="json")
    assert not CandidateExperience.objects.filter(pk=first["experience"][0]["id"]).exists()


def test_cannot_update_another_users_items(api, make_user):
    victim = APIClient()
    victim.force_authenticate(make_user("victim@example.com"))
    victim_skill = victim.put("/api/profile/", profile_payload(), format="json").json()["skills"][0]

    api.put("/api/profile/", profile_payload(skills=[{"id": victim_skill["id"], "name": "Hijacked"}]), format="json")

    assert victim.get("/api/profile/").json()["skills"][0]["name"] == "Python"
    assert CandidateSkill.objects.get(pk=victim_skill["id"]).name == "Python"


def test_duplicate_ids_in_payload_create_rather_than_merge(api):
    first = api.put("/api/profile/", profile_payload(), format="json").json()
    skill = first["skills"][0]
    body = api.put(
        "/api/profile/", profile_payload(skills=[skill, {**skill, "name": "Copy"}]), format="json"
    ).json()
    assert [s["name"] for s in body["skills"]] == ["Python", "Copy"]
    assert len({s["id"] for s in body["skills"]}) == 2


def test_draft_items_have_no_ids(api, ready_job):
    draft = api.get(f"/api/resumes/jobs/{ready_job.pk}/draft/").json()
    assert all(item["id"] is None for item in draft["skills"] + draft["experience"])
