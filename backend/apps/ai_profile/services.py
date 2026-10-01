from django.core.cache import cache
from django.utils import timezone

from apps.candidates.models import CandidateProfile
from apps.candidates.services import CandidateProfileService
from apps.knowledge_base.chunking import ChunkSpec, build_chunks
from apps.knowledge_base.services import CandidateRetrievalService

from .models import SECTIONS, EmployerProfile, ProfileAccessEvent, new_token
from .public import ip_hash, user_agent

# Profile sections -> knowledge-base chunk source types the chatbot/matcher may use.
SECTION_SOURCE_TYPES = {
    "summary": ["profile"],
    "experience": ["experience"],
    "projects": ["project"],
    "skills": ["skills"],
    "education": ["education"],
    "certifications": ["certification"],
    "achievements": ["achievement"],
    "notes": ["note"],
}
# Profile payload keys per section, for the public view.
SECTION_KEYS = {
    "experience": "experience",
    "projects": "projects",
    "skills": "skills",
    "education": "education",
    "certifications": "certifications",
    "achievements": "achievements",
    "links": "links",
}
VIEW_DEDUPE_SECONDS = 3600
ALL_SOURCE_TYPES = sorted({t for types in SECTION_SOURCE_TYPES.values() for t in types})
# Profiles under this size are used whole; larger ones are narrowed by vector search.
FULL_PROFILE_CHARS = 24_000


class NotAvailable(Exception):
    """The link is unknown, disabled or expired. Deliberately indistinguishable."""


class EmployerProfileService:
    @staticmethod
    def get_or_create(user) -> EmployerProfile:
        profile, _ = EmployerProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def update(profile: EmployerProfile, data: dict) -> EmployerProfile:
        for field in ("enabled", "chatbot_enabled", "matching_enabled", "expires_at"):
            if field in data:
                setattr(profile, field, data[field])
        if "visible_sections" in data:
            profile.visible_sections = {
                section: bool(data["visible_sections"].get(section, profile.is_visible(section))) for section in SECTIONS
            }
        profile.save()
        return profile

    @staticmethod
    def regenerate_link(profile: EmployerProfile) -> EmployerProfile:
        """Issue a new secret link. The old one stops working immediately."""
        profile.token = new_token()
        profile.token_created_at = timezone.now()
        profile.save(update_fields=["token", "token_created_at", "updated_at"])
        return profile

    @staticmethod
    def resolve(token: str) -> EmployerProfile:
        profile = EmployerProfile.objects.select_related("user").filter(token=token, enabled=True).first()
        if profile is None or (profile.expires_at and profile.expires_at <= timezone.now()):
            raise NotAvailable
        if not CandidateProfile.objects.filter(user=profile.user).exists():
            raise NotAvailable
        return profile

    @staticmethod
    def visible_source_types(profile: EmployerProfile) -> list[str]:
        return [t for section, types in SECTION_SOURCE_TYPES.items() if profile.is_visible(section) for t in types]

    @staticmethod
    def evidence(
        profile: EmployerProfile, queries: list[str], *, source_types: list[str] | None = None, k: int = 8
    ) -> list[ChunkSpec]:
        """The candidate's approved profile data relevant to `queries`, as citable chunks.

        Built from the source-of-truth tables (always current, even while the
        vector index rebuilds) and limited to `source_types` (default: the
        sections the candidate made visible). Small profiles are used whole;
        for large ones the basics and skills are kept and owner-scoped vector
        search picks the rest.
        """
        allowed = set(source_types if source_types is not None else EmployerProfileService.visible_source_types(profile))
        chunks = [c for c in build_chunks(profile.user) if c.source_type in allowed]
        if sum(len(c.text) for c in chunks) <= FULL_PROFILE_CHARS:
            return chunks

        by_key = {c.key: c for c in chunks}
        picked = [c for c in chunks if c.source_type in ("profile", "skills")]
        for query in queries:
            hits = CandidateRetrievalService.search(profile.user, query, k=k, source_types=sorted(allowed))
            picked += [by_key[h.chunk.key] for h in hits if h.chunk.key in by_key]
        return list({c.key: c for c in picked}.values())

    @staticmethod
    def public_view(profile: EmployerProfile) -> dict:
        """Only the sections the candidate chose to show, without internal ids or provenance."""
        data = CandidateProfileService.get(profile.user) or {}
        view = {"full_name": data.get("full_name"), "headline": data.get("headline")}
        if profile.is_visible("summary"):
            view["summary"] = data.get("summary")
            view["location"] = data.get("location")
        if profile.is_visible("contact"):
            view["email"] = data.get("email")
            view["phone"] = data.get("phone")
        for section, key in SECTION_KEYS.items():
            if profile.is_visible(section):
                view[key] = [
                    {k: v for k, v in item.items() if k not in ("id", "source_type")} for item in data.get(key, [])
                ]
        return view

    @staticmethod
    def log_event(profile: EmployerProfile, kind: str, request) -> None:
        hashed = ip_hash(request)
        if kind == ProfileAccessEvent.Kind.VIEW:
            # One view per visitor per hour, so refreshes don't inflate the count.
            if not cache.add(f"profile-view:{profile.pk}:{hashed}", 1, timeout=VIEW_DEDUPE_SECONDS):
                return
        ProfileAccessEvent.objects.create(profile=profile, kind=kind, ip_hash=hashed, user_agent=user_agent(request))

    @staticmethod
    def activity(profile: EmployerProfile) -> dict:
        events = profile.access_events.all()
        return {
            "views": events.filter(kind=ProfileAccessEvent.Kind.VIEW).count(),
            "unique_visitors": events.filter(kind=ProfileAccessEvent.Kind.VIEW).values("ip_hash").distinct().count(),
            "events": events,
        }
