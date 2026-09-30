from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.ai.providers.fake import FakeProvider


@pytest.fixture
def make_user(db):
    def _make(email="jane@example.com"):
        return get_user_model().objects.create_user(email=email, password="S3cure-pass-123")

    return _make


@pytest.fixture
def user(make_user):
    return make_user()


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def fake_provider():
    """Replace the configured AI provider with a FakeProvider for the test."""
    provider = FakeProvider()
    with mock.patch("apps.resume_parser.services.get_provider", return_value=provider):
        yield provider
