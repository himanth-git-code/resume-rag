from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai.providers.base import StructuredResult
from apps.candidates.models import CandidateNote
from apps.candidates.services import CandidateProfileService
from apps.websites import bio as bio_module
from apps.websites.bio import BioDraft, BioService
from apps.websites.models import PreviewToken, Website, WebsiteEvent
from apps.websites.services import WebsiteService

PROFILE = {
    "full_name": "Jane Doe",
    "headline": "Senior Backend Engineer",
    "summary": "Builds payment systems.",
    "email": "jane@example.com",
    "location": "Berlin",
    "skills": [{"name": "Python", "category": "Languages"}, {"name": "PostgreSQL"}],
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Engineering Lead",
            "responsibilities": ["Led a team of six engineers"],
            "achievements": ["Cut p95 latency by 40%"],
            "technologies": ["Django", "Redis"],
        }
    ],
    "projects": [{"name": "Ledger", "technologies": ["Kafka"]}, {"name": "Side project"}],
    "achievements": [{"title": "Speaker at PyCon"}],
    "links": [{"label": "GitHub", "url": "https://github.com/jane"}],
}


@pytest.fixture
def profile(user):
    with mock.patch("apps.candidates.services.QuestionGenerationService.schedule_initial"):
        return CandidateProfileService.save(user, PROFILE)


@pytest.fixture
def site(user):
    return WebsiteService.get_or_create(user)


def put(api, body):
    return api.put("/api/website/", body, format="json")


# ----- slug ---------------------------------------------------------------

@pytest.mark.parametrize("slug", ["ab", "-jane", "jane-", "Jane Doe", "jäne", "a" * 41, "admin", "portfolio"])
def test_invalid_or_reserved_slugs_are_rejected(api, slug):
    assert put(api, {"slug": slug}).status_code == 400


def test_slug_is_unique_and_case_insensitive(api, make_user, profile):
    assert put(api, {"slug": "Jane-Doe"}).json()["slug"] == "jane-doe"
    other = APIClient()
    other.force_authenticate(make_user("bob@example.com"))
    assert other.put("/api/website/", {"slug": "jane-doe"}, format="json").status_code == 400
    assert other.get("/api/website/slug-available/?slug=JANE-DOE").json()["available"] is False


def test_slug_is_suggested_from_the_name(api, profile):
    assert api.get("/api/website/").json()["suggested_slug"] == "jane-doe"


# ----- render contract ----------------------------------------------------

def test_site_data_uses_visible_sections_and_never_internal_fields(user, profile, site):
    CandidateNote.objects.create(user=user, title="Private", body="secret plans")
    WebsiteService.update(site, {"template": "executive"})
    data = WebsiteService.build_site_data(site)

    assert data["hero"] == {"name": "Jane Doe", "headline": "Senior Backend Engineer", "tagline": None, "location": "Berlin"}
    keys = [s["key"] for s in data["sections"]]
    assert keys[0] == "about" and "experience" in keys and "contact" in keys
    assert "leadership" not in keys  # nothing selected yet: empty sections are omitted
    text = str(data)
    assert "secret plans" not in text
    assert "'id'" not in text and "source_type" not in text
    assert data["content"]["about"]["text"] == "Builds payment systems."


def test_hidden_sections_featured_items_titles_and_leadership(profile, site):
    ledger_id = profile["projects"][0]["id"]
    WebsiteService.update(site, {"template": "technical"})
    WebsiteService.update(
        site,
        {
            "sections": [{"key": "certifications", "visible": False}, {"key": "projects", "visible": True}],
            "overrides": {
                "tagline": "I make APIs fast.",
                "titles": {"projects": "Selected work"},
                "featured_projects": [ledger_id],
            },
        },
    )
    data = WebsiteService.build_site_data(site)
    keys = [s["key"] for s in data["sections"]]
    assert keys[0] == "projects"  # the candidate's order wins
    assert data["sections"][0]["title"] == "Selected work"
    assert [p["name"] for p in data["content"]["projects"]] == ["Ledger"]
    assert data["content"]["github"] == {"label": "GitHub", "url": "https://github.com/jane"}
    assert data["content"]["tech_stack"]["also_used"] == ["Django", "Kafka", "Redis"]
    assert data["meta"]["description"] == "I make APIs fast."

    WebsiteService.update(site, {"template": "executive"})
    WebsiteService.update(site, {"overrides": {"leadership": ["Led a team of six engineers", "Invented bullet"]}})
    data = WebsiteService.build_site_data(site)
    assert data["content"]["leadership"] == ["Led a team of six engineers"]  # only real profile bullets


def test_switching_template_keeps_hidden_choices(api, profile):
    put(api, {"sections": [{"key": "skills", "visible": False}]})
    body = put(api, {"template": "minimal"}).json()
    assert {s["key"]: s["visible"] for s in body["sections"]}["skills"] is False
    assert [s["key"] for s in body["sections"]] == ["about", "experience", "skills", "projects", "education", "contact"]


def test_sections_unknown_to_the_template_are_ignored(api):
    body = put(api, {"sections": [{"key": "github", "visible": True}]}).json()  # modern has no github section
    assert "github" not in [s["key"] for s in body["sections"]]


# ----- bio ----------------------------------------------------------------

class Model:
    def __init__(self, text):
        self.text, self.prompts = text, []

    def generate_structured(self, *, system, prompt, schema):
        self.prompts.append(prompt)
        return StructuredResult(output=BioDraft(text=self.text), model="m")


def test_ai_bio_is_drafted_but_only_published_once_saved(api, user, profile, site, django_capture_on_commit_callbacks):
    CandidateNote.objects.create(user=user, title="Private", body="secret plans")
    model = Model("Jane is a backend engineer who builds payment systems.")
    with mock.patch.object(bio_module, "get_provider", return_value=model), django_capture_on_commit_callbacks(execute=True):
        body = api.post("/api/website/bio/draft/", {"person": "third"}, format="json").json()
    site.refresh_from_db()
    assert site.bio_draft_status == "done"
    assert "secret plans" not in model.prompts[0] and "jane@example.com" not in model.prompts[0]
    assert "third person" in model.prompts[0]
    assert body["bio"]["text"] == ""
    # The draft isn't on the site until the candidate saves it.
    assert WebsiteService.build_site_data(site)["content"]["about"]["text"] == "Builds payment systems."

    saved = put(api, {"bio_text": site.bio_draft_text}).json()["bio"]
    assert saved["source"] == "ai" and saved["approved_at"]
    edited = put(api, {"bio_text": "My own words."}).json()["bio"]
    assert edited["source"] == "candidate"
    site.refresh_from_db()
    assert WebsiteService.build_site_data(site)["content"]["about"]["text"] == "My own words."


def test_bio_draft_failure_and_stale_drafts(site, profile):
    with mock.patch("apps.websites.tasks.draft_bio.delay"):
        BioService.request_draft(site, "first")
        site.refresh_from_db()
        assert site.bio_draft_status == "pending"
        BioService.request_draft(site, "first")  # in flight: not re-queued
        Website.objects.filter(pk=site.pk).update(bio_draft_requested_at=timezone.now() - timedelta(minutes=10))
        with mock.patch.object(bio_module.transaction, "on_commit", side_effect=lambda fn: fn()):
            BioService.request_draft(site, "first")
    BioService.mark_failed(site.pk)
    site.refresh_from_db()
    assert site.bio_draft_status == "failed"


# ----- preview ------------------------------------------------------------

def test_preview_token_renders_until_it_expires(api, profile):
    path = api.post("/api/website/preview/").json()["path"]
    token = path.removeprefix("/portfolio-preview/")
    public = APIClient()

    response = public.get(f"/api/website/render/preview/{token}/")
    assert response.status_code == 200 and response.json()["hero"]["name"] == "Jane Doe"
    public.get(f"/api/website/render/preview/{token}/")
    assert WebsiteEvent.objects.filter(kind="preview_opened").count() == 1  # audited once per token

    PreviewToken.objects.filter(token=token).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert public.get(f"/api/website/render/preview/{token}/").status_code == 404
    assert public.get("/api/website/render/preview/made-up/").status_code == 404


def test_website_endpoints_are_private(api, make_user, profile):
    put(api, {"overrides": {"tagline": "Mine"}})
    other = APIClient()
    other.force_authenticate(make_user("bob@example.com"))
    assert other.get("/api/website/").json()["overrides"]["tagline"] == ""
    assert APIClient().get("/api/website/").status_code == 403
    assert APIClient().post("/api/website/preview/").status_code == 403


def test_publish_problems(api, site):
    problems = api.get("/api/website/").json()["publish_problems"]
    assert "Save your profile first." in problems and "Choose a web address for your site." in problems
