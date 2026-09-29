from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_health_ok(client):
    with mock.patch.dict("config.health.CHECKS", {"redis": mock.Mock()}):
        response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "redis": "ok"}


@pytest.mark.django_db
def test_health_reports_failed_dependency(client):
    with mock.patch.dict(
        "config.health.CHECKS", {"redis": mock.Mock(side_effect=ConnectionError("down"))}
    ):
        response = client.get(reverse("health"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "ok"
    assert body["redis"] == "error"
    assert "down" not in response.content.decode()
