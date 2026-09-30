"""Candidate knowledge base: approved profile data and notes, chunked and embedded.

Postgres structured data (apps.candidates) stays the source of truth; these
tables exist only for semantic retrieval and are fully rebuildable from it.
Every row is owned by one candidate and every query must filter by owner.
"""

from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class KnowledgeChunk(models.Model):
    class SourceType(models.TextChoices):
        PROFILE = "profile", "Profile"
        EXPERIENCE = "experience", "Experience"
        PROJECT = "project", "Project"
        EDUCATION = "education", "Education"
        CERTIFICATION = "certification", "Certification"
        ACHIEVEMENT = "achievement", "Achievement"
        SKILLS = "skills", "Skills"
        NOTE = "note", "Note"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="knowledge_chunks")
    # Stable identity within the owner's knowledge base, e.g. "experience:12", "note:5:0".
    key = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    # Row in the source table (CandidateExperience.pk, CandidateNote.pk, ...); null for grouped chunks.
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    text = models.TextField()
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "key"], name="unique_chunk_key_per_owner")]
        indexes = [models.Index(fields=["owner", "source_type"])]

    def __str__(self):
        return f"{self.key} ({self.owner_id})"


class ChunkEmbedding(models.Model):
    chunk = models.ForeignKey(KnowledgeChunk, on_delete=models.CASCADE, related_name="embeddings")
    model = models.CharField(max_length=100)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIMENSIONS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["chunk", "model"], name="unique_embedding_per_model")]
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]


class KnowledgeBaseState(models.Model):
    class Status(models.TextChoices):
        IDLE = "idle", "Idle"
        INDEXING = "indexing", "Indexing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="knowledge_base_state")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDLE)
    chunk_count = models.PositiveIntegerField(default=0)
    indexed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
