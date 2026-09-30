from unittest import mock

import pytest
from celery.exceptions import Retry
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.ai.errors import AIPermanentError, AITransientError
from apps.ai.providers.fake import FakeEmbeddingProvider
from apps.candidates.models import CandidateExperience, CandidateNote
from apps.candidates.services import CandidateProfileService
from apps.knowledge_base.chunking import build_chunks
from apps.knowledge_base.models import ChunkEmbedding, KnowledgeBaseState, KnowledgeChunk
from apps.knowledge_base.services import CandidateRetrievalService, KnowledgeBaseService
from apps.knowledge_base.tasks import rebuild_knowledge_base

PROFILE = {
    "full_name": "Jane Doe",
    "headline": "Senior Backend Engineer",
    "summary": "Builds reliable payment systems.",
    "location": "Berlin",
    "skills": [
        {"name": "Python", "category": "Languages"},
        {"name": "Go", "category": "Languages"},
        {"name": "PostgreSQL", "category": None},
    ],
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Senior Backend Engineer",
            "start_date": "Jan 2020",
            "is_current": True,
            "responsibilities": ["Built payment APIs"],
            "achievements": ["Introduced Redis caching, cutting p95 latency by 40%"],
            "technologies": ["Django", "Redis"],
        }
    ],
    "projects": [{"name": "Ledger", "description": "Double-entry accounting service", "technologies": ["Kafka"]}],
}


@pytest.fixture
def embedder():
    provider = FakeEmbeddingProvider(dimensions=1024)
    with mock.patch("apps.knowledge_base.services.get_embedding_provider", return_value=provider):
        yield provider


def save_profile(user, **overrides):
    """Save like the profile form does: start from the saved profile (with item ids) if there is one."""
    current = CandidateProfileService.get(user) or PROFILE
    return CandidateProfileService.save(user, {**current, **overrides})


def test_chunks_cover_approved_profile_and_notes(user):
    save_profile(user)
    CandidateNote.objects.create(user=user, title="Leadership", body="Led a team of five engineers.")

    chunks = {c.key: c for c in build_chunks(user)}
    experience = CandidateExperience.objects.get()

    assert set(chunks) >= {"profile", f"experience:{experience.pk}", "skills:Languages", "skills:-"}
    assert any(k.startswith("project:") for k in chunks)
    assert any(k.startswith("note:") for k in chunks)
    role = chunks[f"experience:{experience.pk}"]
    assert role.source_id == experience.pk
    assert "Senior Backend Engineer at Acme Corp" in role.text
    assert "Period: Jan 2020 – Present" in role.text
    assert "Redis caching" in role.text
    assert chunks["skills:Languages"].text == "Skills (Languages): Python, Go"


def test_chunking_is_deterministic(user):
    save_profile(user)
    assert build_chunks(user) == build_chunks(user)


def test_long_notes_are_split_on_paragraphs(user):
    body = "\n\n".join(f"Paragraph {i} " + "x" * 600 for i in range(5))
    CandidateNote.objects.create(user=user, title="Long", body=body)
    notes = [c for c in build_chunks(user) if c.source_type == "note"]
    assert len(notes) > 1
    assert all(len(c.text) < 1700 for c in notes)


def test_rebuild_is_incremental(user, embedder):
    save_profile(user)
    first = KnowledgeBaseService.rebuild(user)
    assert first.embedded == first.total > 0
    assert ChunkEmbedding.objects.filter(chunk__owner=user).count() == first.total

    again = KnowledgeBaseService.rebuild(user)
    assert again.embedded == 0

    role = CandidateProfileService.get(user)["experience"][0]
    save_profile(user, experience=[{**role, "title": "Staff Engineer"}])
    changed = KnowledgeBaseService.rebuild(user)
    assert changed.embedded == 1
    assert "Staff Engineer" in embedder.calls[-1]["texts"][0]
    assert embedder.calls[-1]["input_type"] == "document"

    state = KnowledgeBaseState.objects.get(owner=user)
    assert state.status == "ready" and state.chunk_count == changed.total and state.indexed_at


def test_removed_data_leaves_the_knowledge_base(user, embedder):
    save_profile(user)
    note = CandidateNote.objects.create(user=user, title="Side project", body="Built a chess engine in Rust.")
    KnowledgeBaseService.rebuild(user)
    assert KnowledgeChunk.objects.filter(owner=user, source_type="note").exists()

    note.delete()
    save_profile(user, projects=[])
    result = KnowledgeBaseService.rebuild(user)

    assert result.deleted == 2
    assert not KnowledgeChunk.objects.filter(owner=user, source_type__in=["note", "project"]).exists()


def test_failed_embedding_keeps_existing_knowledge_base(user, embedder):
    save_profile(user)
    KnowledgeBaseService.rebuild(user)
    before = set(KnowledgeChunk.objects.filter(owner=user).values_list("key", "content_hash"))

    save_profile(user, summary="Changed summary", projects=[])
    with mock.patch.object(embedder, "embed", side_effect=AITransientError("down")):
        with pytest.raises(AITransientError):
            KnowledgeBaseService.rebuild(user)

    assert set(KnowledgeChunk.objects.filter(owner=user).values_list("key", "content_hash")) == before


def test_task_records_permanent_failure(user, embedder):
    save_profile(user)
    with mock.patch.object(embedder, "embed", side_effect=AIPermanentError("401")):
        rebuild_knowledge_base.apply(args=[user.pk])
    state = KnowledgeBaseState.objects.get(owner=user)
    assert state.status == "failed" and state.error_code == "ai_error"
    assert cache.get(f"kb-rebuild:{user.pk}") is None  # lock released


def test_task_waits_for_a_running_rebuild(user, embedder):
    cache.add(f"kb-rebuild:{user.pk}", "1")
    try:
        with pytest.raises(Retry):
            rebuild_knowledge_base.apply(args=[user.pk])
        assert embedder.calls == []
    finally:
        cache.delete(f"kb-rebuild:{user.pk}")


def test_search_ranks_the_candidates_own_chunks(user, embedder):
    save_profile(user)
    CandidateNote.objects.create(user=user, title="Hobby", body="Marathon running and cooking.")
    KnowledgeBaseService.rebuild(user)

    results = CandidateRetrievalService.search(user, "Redis caching latency", k=3)

    assert results[0].chunk.source_type == "experience"
    assert results[0].score > results[-1].score
    assert embedder.calls[-1]["input_type"] == "query"

    only_notes = CandidateRetrievalService.search(user, "Redis caching", source_types=["note"])
    assert {r.chunk.source_type for r in only_notes} == {"note"}


def test_search_never_returns_another_candidates_chunks(user, make_user, embedder):
    other = make_user("bob@example.com")
    save_profile(user, experience=[], projects=[], skills=[])
    # Bob's data matches the query far better than Jane's.
    save_profile(other, summary="Redis caching expert", experience=PROFILE["experience"])
    KnowledgeBaseService.rebuild(user)
    KnowledgeBaseService.rebuild(other)

    results = CandidateRetrievalService.search(user, "Redis caching", k=50)

    assert results
    assert {r.chunk.owner_id for r in results} == {user.pk}


def test_profile_save_and_notes_trigger_rebuild(api, user, embedder, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        api.put("/api/profile/", PROFILE, format="json")
    assert KnowledgeBaseState.objects.get(owner=user).status == "ready"
    count = KnowledgeChunk.objects.filter(owner=user).count()

    with django_capture_on_commit_callbacks(execute=True):
        api.post("/api/notes/", {"title": "Mentoring", "body": "Mentored two juniors."}, format="json")
    assert KnowledgeChunk.objects.filter(owner=user).count() == count + 1

    kb = api.get("/api/me/").json()["knowledge_base"]
    assert kb["status"] == "ready" and kb["chunk_count"] == count + 1


@pytest.mark.django_db
def test_me_reports_idle_knowledge_base_for_new_users(make_user):
    client = APIClient()
    client.force_authenticate(make_user("new@example.com"))
    assert client.get("/api/me/").json()["knowledge_base"] == {"status": "idle", "chunk_count": 0, "indexed_at": None}
