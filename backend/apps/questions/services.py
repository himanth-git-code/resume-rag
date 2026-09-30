import logging
import re
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.ai.providers import get_provider

from .models import Question, QuestionGeneration
from .prompts import QUESTION_SYSTEM, question_prompt
from .schemas import QuestionBatch
from .sections import ProfileItems, Section, build_more_section, build_section, plan_full

logger = logging.getLogger(__name__)

Status = QuestionGeneration.Status
Kind = QuestionGeneration.Kind

# A generation still pending/running after this long is assumed lost (e.g. the worker died).
STALE_AFTER = timedelta(minutes=30)

FAILURE_MESSAGES = {
    "ai_unavailable": "The question service is busy right now. Please try again in a few minutes.",
    "ai_error": "Something went wrong while generating questions. Please try again.",
}


class NoProfile(Exception):
    pass


class GenerationInProgress(Exception):
    pass


class InvalidScope(Exception):
    pass


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", text.lower())).strip()


class QuestionGenerationService:
    @staticmethod
    def latest(user) -> QuestionGeneration | None:
        return QuestionGeneration.objects.filter(owner=user).first()

    @staticmethod
    def profile_changed(user) -> bool:
        """True if the profile or notes changed since the current question set was generated."""
        last = QuestionGeneration.objects.filter(owner=user, kind=Kind.FULL, status=Status.DONE).first()
        return last is not None and last.source_hash != ProfileItems(user).fingerprint()

    @staticmethod
    def start_full(user) -> QuestionGeneration:
        items = ProfileItems(user)
        if not items.exists:
            raise NoProfile
        return QuestionGenerationService._start(
            user, kind=Kind.FULL, sections=plan_full(items), source_hash=items.fingerprint()
        )

    @staticmethod
    def start_more(user, *, category: str | None, source: str | None) -> QuestionGeneration:
        if category and category not in Question.Category.values:
            raise InvalidScope("Unknown category")
        items = ProfileItems(user)
        if not items.exists:
            raise NoProfile
        if source and source not in items.by_ref:
            raise InvalidScope("Unknown source")
        scope = {k: v for k, v in (("category", category), ("source", source)) if v}
        section = build_more_section(scope, items, [])
        if section is None:
            raise InvalidScope("Nothing to generate questions about")
        return QuestionGenerationService._start(user, kind=Kind.MORE, sections=[section.key], scope=scope)

    @staticmethod
    def schedule_initial(user) -> None:
        """Proactively generate a first question set (SPEC §8), once per candidate."""
        if QuestionGeneration.objects.filter(owner=user).exists():
            return
        try:
            QuestionGenerationService.start_full(user)
        except (NoProfile, GenerationInProgress):
            pass

    @staticmethod
    def _start(user, *, kind, sections, source_hash="", scope=None) -> QuestionGeneration:
        from .tasks import generate_questions

        with transaction.atomic():
            # Lock the candidate's generations so two requests can't both start one.
            in_flight = QuestionGeneration.objects.select_for_update().filter(
                owner=user, status__in=[Status.PENDING, Status.RUNNING]
            )
            in_flight.filter(created_at__lt=timezone.now() - STALE_AFTER).update(
                status=Status.FAILED,
                error_code="stale",
                error_message=FAILURE_MESSAGES["ai_error"],
                completed_at=timezone.now(),
            )
            if in_flight.exists():
                raise GenerationInProgress
            if kind == Kind.FULL:
                # Leftovers of an earlier regeneration that never finished.
                Question.objects.filter(owner=user, is_active=False).delete()
            generation = QuestionGeneration.objects.create(
                owner=user, kind=kind, sections=sections, source_hash=source_hash, scope=scope or {}
            )
            transaction.on_commit(lambda: generate_questions.delay(generation.pk))
        return generation

    @staticmethod
    def run(generation_id: int) -> None:
        """Generate the remaining sections of a generation. Idempotent and resumable.

        Each section is saved as it completes, so a retry continues where the last
        attempt stopped. A regeneration's questions stay hidden until every section
        has succeeded, so a failure never wipes the candidate's current set.
        Raises AITransientError for the task to retry.
        """
        with transaction.atomic():
            gen = QuestionGeneration.objects.select_for_update().get(pk=generation_id)
            if gen.status not in (Status.PENDING, Status.RUNNING):
                return
            gen.status = Status.RUNNING
            gen.save(update_fields=["status"])

        user = gen.owner
        items = ProfileItems(user)
        # The first-ever set is shown section by section; later full sets swap in when complete.
        show_now = gen.kind == Kind.MORE or not (
            Question.objects.filter(owner=user, is_active=True).exclude(generation=gen).exists()
        )
        provider = get_provider()

        for key in gen.sections:
            if key in gen.completed_sections:
                continue
            section = QuestionGenerationService._section(gen, key, items)
            if section is not None:
                result = provider.generate_structured(
                    system=QUESTION_SYSTEM, prompt=question_prompt(section), schema=QuestionBatch
                )
                gen.model = result.model
                QuestionGenerationService._save_section(gen, section, result.output, items, active=show_now)
            with transaction.atomic():
                gen.completed_sections = [*gen.completed_sections, key]
                gen.save(update_fields=["completed_sections", "model"])

        with transaction.atomic():
            if gen.kind == Kind.FULL:
                Question.objects.filter(owner=user).exclude(generation=gen).delete()
                Question.objects.filter(generation=gen).update(is_active=True)
            gen.status = Status.DONE
            gen.completed_at = timezone.now()
            gen.save(update_fields=["status", "completed_at"])
        logger.info("Question generation %s done: %s sections", gen.pk, len(gen.sections))

    @staticmethod
    def mark_failed(generation_id: int, code: str) -> None:
        QuestionGeneration.objects.filter(pk=generation_id, status__in=[Status.PENDING, Status.RUNNING]).update(
            status=Status.FAILED,
            error_code=code,
            error_message=FAILURE_MESSAGES.get(code, FAILURE_MESSAGES["ai_error"]),
            completed_at=timezone.now(),
        )

    @staticmethod
    def _section(gen: QuestionGeneration, key: str, items: ProfileItems) -> Section | None:
        if gen.kind == Kind.MORE:
            existing = list(
                Question.objects.filter(owner=gen.owner, is_active=True, parent=None).values_list("text", flat=True)
            )
            return build_more_section(gen.scope, items, existing)
        return build_section(key, items)  # None if the item was deleted since planning

    @staticmethod
    def _save_section(gen, section: Section, batch: QuestionBatch, items: ProfileItems, *, active: bool) -> None:
        allowed = section.refs
        default_refs = [next(iter(allowed))] if len(allowed) == 1 else []
        # A full set replaces the current one, so it only dedupes within itself;
        # "more" must also avoid the questions the candidate already has.
        scope = Q(generation=gen)
        if gen.kind == Kind.MORE:
            scope |= Q(is_active=True)
        seen = {normalise(t) for t in Question.objects.filter(scope, owner=gen.owner).values_list("text", flat=True)}
        order = Question.objects.filter(generation=gen).count()

        def points(raw):
            return [
                {"ref": p.ref, "label": items.by_ref[p.ref].label, "text": p.text.strip()[:500]}
                for p in raw
                if p.ref in allowed and p.text.strip()
            ]

        with transaction.atomic():
            for q in batch.questions:
                key = normalise(q.text)
                if not key or key in seen:
                    continue
                seen.add(key)
                category = q.category if q.category in section.categories else section.categories[0]
                refs = [r for r in dict.fromkeys(q.refs) if r in allowed] or default_refs
                parent = Question.objects.create(
                    owner=gen.owner,
                    generation=gen,
                    is_active=active,
                    section=section.key,
                    category=category,
                    difficulty=q.difficulty,
                    topic=q.topic.strip()[:200],
                    text=q.text.strip(),
                    source_refs=refs,
                    talking_points=points(q.talking_points),
                    order=order,
                )
                order += 1
                for i, f in enumerate(q.follow_ups):
                    if not f.text.strip():
                        continue
                    Question.objects.create(
                        owner=gen.owner,
                        generation=gen,
                        parent=parent,
                        is_active=active,
                        section=section.key,
                        category=category,
                        difficulty=f.difficulty,
                        topic=parent.topic,
                        text=f.text.strip(),
                        source_refs=refs,
                        talking_points=points(f.talking_points),
                        order=i,
                    )


class QuestionQueryService:
    """Read side: the candidate's active questions, with filters and facets."""

    @staticmethod
    def list(user, *, category=None, source=None, difficulty=None, search=None):
        qs = Question.objects.filter(owner=user, is_active=True, parent=None)
        if category:
            qs = qs.filter(category=category)
        if source:
            qs = qs.filter(source_refs__contains=[source])
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        if search:
            qs = qs.filter(text__icontains=search)
        return qs.order_by("section", "order", "pk").prefetch_related("follow_ups")

    @staticmethod
    def facets(user) -> dict:
        questions = Question.objects.filter(owner=user, is_active=True, parent=None)
        categories = {c: 0 for c in Question.Category.values}
        ref_counts: dict[str, int] = {}
        for category, refs in questions.values_list("category", "source_refs"):
            categories[category] += 1
            for ref in refs:
                ref_counts[ref] = ref_counts.get(ref, 0) + 1

        items = ProfileItems(user)
        type_order = ["experience", "project", "skill", "education", "certification", "achievement", "note", "profile"]
        sources = sorted(
            (
                {"ref": ref, "label": items.by_ref[ref].label, "type": ref.split(":")[0], "count": count}
                for ref, count in ref_counts.items()
                if ref in items.by_ref  # items deleted since generation drop out of the filter
            ),
            key=lambda s: (type_order.index(s["type"]) if s["type"] in type_order else 99, s["label"].lower()),
        )
        return {"total": sum(categories.values()), "categories": categories, "sources": sources}
