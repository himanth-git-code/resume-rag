import json

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

AUTH = "/_allauth/browser/v1/auth"


def post_json(client, url, data, **extra):
    return client.post(url, data=json.dumps(data), content_type="application/json", **extra)


@pytest.mark.django_db
def test_signup_creates_user_and_session(client):
    response = post_json(client, f"{AUTH}/signup", {"email": "New@Example.com", "password": "S3cure-pass-123"})

    assert response.status_code == 200
    assert response.json()["data"]["user"]["email"] == "new@example.com"
    assert get_user_model().objects.filter(email="new@example.com").exists()
    assert client.get(reverse("me")).status_code == 200


def test_login_logout_roundtrip(client, user):
    response = post_json(client, f"{AUTH}/login", {"email": "JANE@example.com", "password": "S3cure-pass-123"})
    assert response.status_code == 200
    assert client.get(f"{AUTH}/session").status_code == 200

    response = client.delete(f"{AUTH}/session")
    assert response.status_code == 401
    assert client.get(f"{AUTH}/session").status_code == 401


def test_login_rejects_wrong_password(client, user):
    response = post_json(client, f"{AUTH}/login", {"email": "jane@example.com", "password": "wrong-pass"})
    assert response.status_code == 400


def test_login_requires_csrf_token_from_session_endpoint(user):
    client = Client(enforce_csrf_checks=True)

    assert post_json(client, f"{AUTH}/login", {"email": "jane@example.com", "password": "S3cure-pass-123"}).status_code == 403

    client.get(f"{AUTH}/session")  # sets the csrftoken cookie, as the SPA does on load
    token = client.cookies["csrftoken"].value
    response = post_json(
        client,
        f"{AUTH}/login",
        {"email": "jane@example.com", "password": "S3cure-pass-123"},
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_me_requires_authentication(client):
    assert client.get(reverse("me")).status_code == 403


def test_me_returns_current_user(client, user):
    client.force_login(user)
    response = client.get(reverse("me"))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "jane@example.com"
    assert body["dashboard"] == {
        "has_resume": False,
        "latest_parse_status": None,
        "latest_job_id": None,
        "has_profile": False,
    }


@pytest.mark.django_db
def test_email_is_unique_case_insensitively():
    User = get_user_model()
    User.objects.create_user(email="dup@example.com", password="x")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="DUP@example.com", password="x")


def _providers(client):
    data = client.get("/_allauth/browser/v1/config").json()["data"]
    return [p["id"] for p in data["socialaccount"]["providers"]]


@pytest.mark.django_db
def test_google_hidden_when_not_configured(client, settings):
    settings.SOCIALACCOUNT_PROVIDERS = {}
    assert _providers(client) == []


@pytest.mark.django_db
def test_google_listed_when_configured(client, settings):
    settings.SOCIALACCOUNT_PROVIDERS = {
        "google": {"APPS": [{"client_id": "cid", "secret": "secret"}]},
    }
    assert _providers(client) == ["google"]
