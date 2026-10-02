from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.ai.providers.base import StructuredResult
from apps.ai_profile.models import JobMatchRequest
from apps.ai_profile.services import EmployerProfileService
from apps.candidates.services import CandidateProfileService
from apps.chatbot import services as chat_services
from apps.chatbot.models import EmployerChatMessage, EmployerChatSession
from apps.chatbot.schemas import ChatAnswer
from apps.websites.models import Website, WebsiteEvent
from apps.websites.services import PublishingService, WebsiteService

PROFILE = {
    "full_name": "Jane Doe",
    "headline": "Senior Backend Engineer",
    "summary": "Builds payment systems.",
    "skills": [{"name": "Python"}],
    "experience": [{"company": "Acme Corp", "title": "Engineer", "achievements": ["Cut latency by 40%"]}],
    "projects": [{"name": "Ledger", "description": "Accounting service"}],
}
JD = "Backend Engineer. " + "We need strong Python and PostgreSQL experience, API design and mentoring. " * 5


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def save_profile(user, data):
    with mock.patch("apps.candidates.services.QuestionGenerationService.schedule_initial"):
        return CandidateProfileService.save(user, data)


@pytest.fixture
def site(api, user):
    save_profile(user, PROFILE)
    api.put("/api/website/", {"slug": "jane-doe", "show_matching": True}, format="json")
    return Website.objects.get(user=user)


def publish(api):
    return api.post("/api/website/publish/")


def visit(slug="jane-doe", ip="203.0.113.7"):
    return APIClient().get(f"/api/public/sites/{slug}/", HTTP_X_FORWARDED_FOR=ip)


def test_publish_problems_block_publishing(api):
    response = publish(api)
    assert response.status_code == 409
    assert "Save your profile first." in response.json()["problems"]


def test_published_site_is_a_snapshot(api, user, site):
    body = publish(api).json()
    assert body["publish"]["published"] is True and body["publish"]["version"] == 1
    assert body["publish"]["path"] == "/portfolio/jane-doe" and body["publish"]["has_changes"] is False

    live = visit().json()
    assert live["hero"]["name"] == "Jane Doe"
    assert live["widgets"]["slug"] == "jane-doe"

    # Edits after publishing don't reach the live site until republished.
    current = CandidateProfileService.get(user)
    save_profile(user, {**current, "headline": "Staff Engineer"})
    api.put("/api/website/", {"overrides": {"tagline": "Draft tagline"}}, format="json")
    assert visit().json()["hero"]["headline"] == "Senior Backend Engineer"
    assert api.get("/api/website/").json()["publish"]["has_changes"] is True

    body = publish(api).json()
    assert body["publish"]["version"] == 2 and body["publish"]["has_changes"] is False
    assert visit().json()["hero"] == {
        "name": "Jane Doe", "headline": "Staff Engineer", "tagline": "Draft tagline", "location": None
    }


def test_unpublished_unknown_and_renamed_sites_are_404(api, site):
    assert visit().status_code == 404  # not yet published
    publish(api)
    assert visit("JANE-DOE").status_code == 200  # case-insensitive
    api.put("/api/website/", {"slug": "jane-builds"}, format="json")
    assert visit("jane-doe").status_code == 404
    assert visit("jane-builds").status_code == 200
    api.post("/api/website/unpublish/")
    assert visit("jane-builds").status_code == 404
    assert visit("nobody").status_code == 404
    kinds = list(WebsiteEvent.objects.values_list("kind", flat=True))
    assert "published" in kinds and "unpublished" in kinds


def test_public_views_are_audited_once_per_visitor(api, site):
    publish(api)
    visit(ip="203.0.113.7")
    visit(ip="203.0.113.7")
    visit(ip="198.51.100.2")
    assert WebsiteEvent.objects.filter(kind="public_view").count() == 2


def test_widgets_need_both_the_site_and_global_switches(api, user, site):
    publish(api)
    assert visit().json()["widgets"]["chatbot"] is True
    assert visit().json()["widgets"]["matching"] is True

    EmployerProfileService.update(EmployerProfileService.get_or_create(user), {"chatbot_enabled": False})
    assert visit().json()["widgets"]["chatbot"] is False
    response = APIClient().post("/api/public/sites/jane-doe/chat/", {"message": "Python?"}, format="json")
    assert response.status_code == 404

    api.put("/api/website/", {"show_matching": False}, format="json")
    assert visit().json()["widgets"]["matching"] is False


class Model:
    def __init__(self):
        self.prompts = []

    def generate_structured(self, *, system, prompt, schema):
        self.prompts.append(prompt)
        return StructuredResult(output=ChatAnswer(answer="", status="not_found"), model="m")


def test_website_chat_uses_only_published_sections_and_its_own_channel(api, user, site):
    # Projects are hidden on the website (but visible on the employer profile).
    api.put("/api/website/", {"sections": [{"key": "projects", "visible": False}]}, format="json")
    publish(api)
    # Showing projects again without republishing must not leak them.
    api.put("/api/website/", {"sections": [{"key": "projects", "visible": True}]}, format="json")

    with mock.patch("apps.chatbot.tasks.answer_message.delay"):
        response = APIClient().post("/api/public/sites/jane-doe/chat/", {"message": "Projects?"}, format="json")
    assert response.status_code == 202
    session = EmployerChatSession.objects.get()
    assert session.channel == "website" and "project" not in session.source_types

    model = Model()
    with mock.patch.object(chat_services, "get_provider", return_value=model):
        chat_services.EmployerChatService.answer(EmployerChatMessage.objects.get(status="pending").pk)
    assert "Acme Corp" in model.prompts[0] and "Ledger" not in model.prompts[0]

    # The website session can't be continued through the employer-profile endpoint, and vice versa.
    employer = EmployerProfileService.update(EmployerProfileService.get_or_create(user), {"enabled": True})
    assert APIClient().get(f"/api/public/p/{employer.token}/chat/{session.public_id}/").status_code == 404
    assert APIClient().get(f"/api/public/sites/jane-doe/chat/{session.public_id}/").status_code == 200

    # The candidate sees it in their conversations, labelled as from the website.
    assert api.get("/api/employer-profile/chats/").json()["results"][0]["channel"] == "website"


def test_website_matching(api, user, site):
    publish(api)
    with mock.patch("apps.ai_profile.tasks.run_job_match.apply_async"):
        response = APIClient().post("/api/public/sites/jane-doe/match/", {"job_description": JD}, format="json")
    assert response.status_code == 202
    match = JobMatchRequest.objects.get()
    assert match.source == "website" and "profile" in match.source_types
    assert APIClient().get(f"/api/public/sites/jane-doe/match/{response.json()['id']}/").status_code == 200
    assert api.get("/api/matches/").json()["results"][0]["source"] == "website"


def test_websites_are_isolated(api, site, make_user):
    publish(api)
    other = APIClient()
    other.force_authenticate(make_user("bob@example.com"))
    assert other.post("/api/website/unpublish/").status_code == 200  # acts on Bob's own (unpublished) site
    assert visit().status_code == 200
    assert other.get("/api/website/").json()["publish"]["published"] is False


def test_source_types_follow_published_sections(api, site):
    publish(api)
    site.refresh_from_db()
    types = PublishingService.source_types(site)
    assert set(types) >= {"profile", "experience", "skills", "project"}
    assert "note" not in types


def test_build_site_data_widgets_are_off_until_published(site):
    assert WebsiteService.build_site_data(site)["widgets"] == {"chatbot": False, "matching": False}
