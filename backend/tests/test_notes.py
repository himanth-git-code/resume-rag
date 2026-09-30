import pytest
from rest_framework.test import APIClient

from apps.candidates.models import CandidateNote


def test_notes_crud(api):
    assert api.get("/api/notes/").json() == []

    created = api.post("/api/notes/", {"title": " Leadership ", "body": "Led a team of 5."}, format="json")
    assert created.status_code == 201
    note = created.json()
    assert note["title"] == "Leadership"

    updated = api.put(f"/api/notes/{note['id']}/", {"title": "Leadership", "body": "Led a team of 6."}, format="json")
    assert updated.status_code == 200
    assert updated.json()["body"] == "Led a team of 6."
    assert [n["id"] for n in api.get("/api/notes/").json()] == [note["id"]]

    assert api.delete(f"/api/notes/{note['id']}/").status_code == 204
    assert not CandidateNote.objects.exists()


@pytest.mark.parametrize("payload", [{"title": "", "body": "x"}, {"title": "x", "body": ""}, {"title": "x", "body": "y" * 10001}])
def test_note_validation(api, payload):
    assert api.post("/api/notes/", payload, format="json").status_code == 400


def test_notes_are_private(api, make_user):
    note_id = api.post("/api/notes/", {"title": "Mine", "body": "secret"}, format="json").json()["id"]

    other = APIClient()
    other.force_authenticate(make_user("mallory@example.com"))
    assert other.get("/api/notes/").json() == []
    assert other.get(f"/api/notes/{note_id}/").status_code == 404
    assert other.put(f"/api/notes/{note_id}/", {"title": "x", "body": "y"}, format="json").status_code == 404
    assert other.delete(f"/api/notes/{note_id}/").status_code == 404
    assert CandidateNote.objects.get(pk=note_id).body == "secret"


@pytest.mark.django_db
def test_notes_require_authentication():
    assert APIClient().get("/api/notes/").status_code == 403
