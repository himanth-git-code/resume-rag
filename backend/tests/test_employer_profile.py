from datetime import timedelta
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai_profile.models import EmployerProfile, ProfileAccessEvent
from apps.ai_profile.public import verify_turnstile
from apps.ai_profile.services import EmployerProfileService
from apps.candidates.services import CandidateProfileService

PROFILE = {
    "full_name": "Jane Doe",
    "headline": "Senior Backend Engineer",
    "summary": "Builds payment systems.",
    "email": "jane@example.com",
    "phone": "+49 123",
    "skills": [{"name": "Python"}],
    "experience": [{"company": "Acme Corp", "title": "Senior Backend Engineer"}],
    "projects": [{"name": "Ledger"}],
}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def live(user):
    """A saved candidate profile with an enabled employer profile."""
    with mock.patch("apps.candidates.services.QuestionGenerationService.schedule_initial"):
        CandidateProfileService.save(user, PROFILE)
    return EmployerProfileService.update(EmployerProfileService.get_or_create(user), {"enabled": True})


def public(path_or_token, client=None, ip="203.0.113.7"):
    client = client or APIClient()
    token = path_or_token.removeprefix("/p/")
    return client.get(f"/api/public/p/{token}/", HTTP_X_FORWARDED_FOR=ip)


def test_settings_default_to_disabled_with_private_sections_hidden(api):
    body = api.get("/api/employer-profile/").json()
    assert body["enabled"] is False
    assert body["has_profile"] is False
    assert body["path"].startswith("/p/") and len(body["path"]) > 40
    assert body["visible_sections"]["contact"] is False
    assert body["visible_sections"]["notes"] is False
    assert body["visible_sections"]["experience"] is True


def test_public_profile_shows_only_visible_sections(api, live):
    api.put("/api/employer-profile/", {"visible_sections": {"projects": False}}, format="json")

    body = public(live.token).json()
    profile = body["profile"]
    assert profile["full_name"] == "Jane Doe"
    assert profile["experience"] == [
        {
            "company": "Acme Corp",
            "title": "Senior Backend Engineer",
            "location": None,
            "start_date": None,
            "end_date": None,
            "is_current": None,
            "description": None,
            "responsibilities": [],
            "achievements": [],
            "technologies": [],
        }
    ]
    assert "projects" not in profile
    assert "email" not in profile and "phone" not in profile  # contact is opt-in
    assert body["chatbot_enabled"] is True
    assert body["turnstile_site_key"] is None


def test_contact_shown_when_enabled(api, live):
    api.put("/api/employer-profile/", {"visible_sections": {"contact": True}}, format="json")
    profile = public(live.token).json()["profile"]
    assert profile["email"] == "jane@example.com"


@pytest.mark.parametrize("scenario", ["unknown", "disabled", "expired", "regenerated", "no_profile"])
def test_unavailable_links_are_indistinguishable(api, user, live, make_user, scenario):
    token = live.token
    if scenario == "unknown":
        token = "not-a-real-token"
    elif scenario == "disabled":
        api.put("/api/employer-profile/", {"enabled": False}, format="json")
    elif scenario == "expired":
        EmployerProfile.objects.filter(pk=live.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
    elif scenario == "regenerated":
        api.post("/api/employer-profile/regenerate-link/")
    elif scenario == "no_profile":
        other = EmployerProfileService.get_or_create(make_user("empty@example.com"))
        token = EmployerProfileService.update(other, {"enabled": True}).token

    response = public(token)
    baseline = public("not-a-real-token", ip="198.51.100.9")
    assert response.status_code == baseline.status_code == 404
    assert response.content == baseline.content


def test_regenerated_link_works(api, live):
    new_path = api.post("/api/employer-profile/regenerate-link/").json()["path"]
    assert public(new_path).status_code == 200


def test_expiry_must_be_in_the_future(api):
    past = (timezone.now() - timedelta(days=1)).isoformat()
    assert api.put("/api/employer-profile/", {"expires_at": past}, format="json").status_code == 400
    assert api.put("/api/employer-profile/", {"visible_sections": {"bogus": True}}, format="json").status_code == 400


def test_views_are_logged_once_per_visitor_with_hashed_ip(api, live):
    public(live.token, ip="203.0.113.7")
    public(live.token, ip="203.0.113.7")
    public(live.token, ip="198.51.100.2")

    events = ProfileAccessEvent.objects.filter(profile=live, kind="view")
    assert events.count() == 2
    assert all("203.0.113.7" not in e.ip_hash and len(e.ip_hash) == 64 for e in events)

    activity = api.get("/api/employer-profile/activity/").json()
    assert activity["views"] == 2 and activity["unique_visitors"] == 2


def test_public_endpoint_is_throttled_per_client_ip(live, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "public_view": "2/hour"}}
    with mock.patch("rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]):
        assert public(live.token, ip="203.0.113.7").status_code == 200
        assert public(live.token, ip="203.0.113.7").status_code == 200
        assert public(live.token, ip="203.0.113.7").status_code == 429
        assert public(live.token, ip="198.51.100.2").status_code == 200  # a different employer isn't affected


def test_public_endpoint_ignores_session_auth(live, user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    assert public(live.token, client=client).status_code == 200


def test_settings_are_per_candidate(api, live, make_user):
    other = APIClient()
    other.force_authenticate(make_user("bob@example.com"))
    assert other.get("/api/employer-profile/").json()["path"] != f"/p/{live.token}"
    assert other.get("/api/employer-profile/activity/").json()["count"] == 0


def test_turnstile_verification(settings, rf):
    request = rf.get("/", REMOTE_ADDR="203.0.113.7")
    settings.TURNSTILE_SECRET_KEY = ""
    assert verify_turnstile(None, request) is True  # disabled locally

    settings.TURNSTILE_SECRET_KEY = "secret"
    assert verify_turnstile(None, request) is False
    with mock.patch("apps.ai_profile.public.requests.post") as post:
        post.return_value.json.return_value = {"success": True}
        assert verify_turnstile("tok", request) is True
        assert post.call_args.kwargs["data"]["response"] == "tok"
        post.return_value.json.return_value = {"success": False}
        assert verify_turnstile("tok", request) is False
        post.side_effect = __import__("requests").ConnectionError()
        assert verify_turnstile("tok", request) is False  # fails closed
