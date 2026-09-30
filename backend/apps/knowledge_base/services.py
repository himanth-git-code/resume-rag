import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from pgvector.django import CosineDistance

from apps.ai.providers import get_embedding_provider

from .chunking import build_chunks
from .models import ChunkEmbedding, KnowledgeBaseState, KnowledgeChunk

logger = logging.getLogger(__name__)

Status = KnowledgeBaseState.Status


@dataclass(frozen=True)
class RebuildResult:
    total: int
    embedded: int
    deleted: int


class KnowledgeBaseService:
    @staticmethod
    def schedule_rebuild(user) -> None:
        """Queue a rebuild after the current transaction commits."""
        from .tasks import rebuild_knowledge_base

        user_id = user.pk
        transaction.on_commit(lambda: rebuild_knowledge_base.delay(user_id))

    @staticmethod
    def rebuild(user) -> RebuildResult:
        """Bring the user's chunks and embeddings in line with their current data.

        Incremental: unchanged chunks keep their embeddings; only new or changed
        text is embedded. Embedding runs before any write, so an AI failure
        leaves the existing knowledge base untouched. Callers must ensure only
        one rebuild per user runs at a time (see tasks.rebuild_knowledge_base).
        """
        provider = get_embedding_provider()
        specs = build_chunks(user)

        existing = {c.key: c for c in KnowledgeChunk.objects.filter(owner=user)}
        embedded_ids = set(
            ChunkEmbedding.objects.filter(chunk__owner=user, model=provider.model).values_list("chunk_id", flat=True)
        )
        stale = [
            spec
            for spec in specs
            if spec.key not in existing
            or existing[spec.key].content_hash != spec.content_hash
            or existing[spec.key].pk not in embedded_ids
        ]
        vectors = provider.embed([spec.text for spec in stale], input_type="document") if stale else []

        with transaction.atomic():
            wanted = {spec.key for spec in specs}
            _, per_model = KnowledgeChunk.objects.filter(owner=user).exclude(key__in=wanted).delete()
            deleted = per_model.get(KnowledgeChunk._meta.label, 0)

            for spec, vector in zip(stale, vectors, strict=True):
                chunk, _ = KnowledgeChunk.objects.update_or_create(
                    owner=user,
                    key=spec.key,
                    defaults={
                        "source_type": spec.source_type,
                        "source_id": spec.source_id,
                        "text": spec.text,
                        "content_hash": spec.content_hash,
                    },
                )
                # One embedding per chunk: drop vectors from older text or other models.
                chunk.embeddings.all().delete()
                ChunkEmbedding.objects.create(chunk=chunk, model=provider.model, embedding=vector)

            KnowledgeBaseState.objects.update_or_create(
                owner=user,
                defaults={
                    "status": Status.READY,
                    "chunk_count": len(specs),
                    "indexed_at": timezone.now(),
                    "error_code": "",
                },
            )

        logger.info("Knowledge base rebuilt for user %s: %s chunks, %s embedded", user.pk, len(specs), len(stale))
        return RebuildResult(total=len(specs), embedded=len(stale), deleted=deleted)

    @staticmethod
    def set_status(user_id: int, status: str, error_code: str = "") -> None:
        KnowledgeBaseState.objects.update_or_create(
            owner_id=user_id, defaults={"status": status, "error_code": error_code}
        )

    @staticmethod
    def state_for(user) -> dict:
        state = KnowledgeBaseState.objects.filter(owner=user).first()
        if state is None:
            return {"status": Status.IDLE, "chunk_count": 0, "indexed_at": None}
        return {
            "status": state.status,
            "chunk_count": state.chunk_count,
            "indexed_at": state.indexed_at.isoformat() if state.indexed_at else None,
        }


@dataclass(frozen=True)
class SearchResult:
    chunk: KnowledgeChunk
    score: float  # cosine similarity, higher is closer


class CandidateRetrievalService:
    @staticmethod
    def search(user, query: str, *, k: int = 8, source_types: list[str] | None = None) -> list[SearchResult]:
        """Semantic search over one candidate's knowledge base.

        The owner filter is applied in the same query as the vector ordering,
        so another candidate's chunks can never be returned.
        """
        provider = get_embedding_provider()
        [vector] = provider.embed([query], input_type="query")

        embeddings = ChunkEmbedding.objects.filter(chunk__owner=user, model=provider.model)
        if source_types:
            embeddings = embeddings.filter(chunk__source_type__in=source_types)
        rows = (
            embeddings.select_related("chunk")
            .annotate(distance=CosineDistance("embedding", vector))
            .order_by("distance")[:k]
        )
        return [SearchResult(chunk=row.chunk, score=1.0 - float(row.distance)) for row in rows]
