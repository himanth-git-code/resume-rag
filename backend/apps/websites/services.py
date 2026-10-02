import re
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.ai_profile.public import ip_hash
from apps.candidates.models import CandidateProfile
from apps.candidates.services import CandidateProfileService

from .catalog import PREMIUM_TEMPLATES, RESERVED_SLUGS, SECTIONS, SLUG_PATTERN, TEMPLATES, default_sections
from .models import PreviewToken, Website, WebsiteEvent, WebsiteVersion

PREVIEW_TTL = timedelta(minutes=30)
SITE_DATA_VERSION = 1


class SlugError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _clean(item: dict) -> dict:
    """Drop internal fields (ids, provenance) from a profile item."""
    return {k: v for k, v in item.items() if k not in ("id", "source_type")}


def _role(e: dict) -> str:
    return " at ".join(v for v in (e.get("title"), e.get("company")) if v) or "Role"


def _github(links: list[dict]) -> dict | None:
    for link in links:
        if "github" in (link.get("label") or "").lower() or "github.com" in (link.get("url") or "").lower():
            return {"label": link.get("label") or "GitHub", "url": link["url"]}
    return None


def _grouped_skills(skills: list[dict]) -> list[dict]:
    groups: dict[str, list[str]] = {}
    for s in skills:
        groups.setdefault(s.get("category") or "", []).append(s["name"])
    return [{"category": k or None, "items": v} for k, v in groups.items()]


def _featured(items: list[dict], ids) -> list[dict]:
    if ids is None:
        return items
    wanted = set(ids)
    return [i for i in items if i.get("id") in wanted]


class WebsiteService:
    @staticmethod
    def get_or_create(user) -> Website:
        website, _ = Website.objects.get_or_create(user=user)
        return website

    # ----- slug -------------------------------------------------------------

    @staticmethod
    def validate_slug(slug: str, website: Website) -> str:
        slug = (slug or "").strip().lower()
        if not re.match(SLUG_PATTERN, slug):
            raise SlugError("Use 3–40 lowercase letters, numbers and hyphens, starting and ending with a letter or number.")
        if slug in RESERVED_SLUGS:
            raise SlugError("That name is reserved. Please choose another.")
        if Website.objects.filter(slug=slug).exclude(pk=website.pk).exists():
            raise SlugError("That name is already taken.")
        return slug

    @staticmethod
    def suggest_slug(website: Website) -> str | None:
        profile = CandidateProfile.objects.filter(user=website.user).first()
        base = slugify(profile.full_name if profile else "")[:36].strip("-")
        if len(base) < 3:
            return None
        for suffix in ["", *range(2, 50)]:
            candidate = f"{base}-{suffix}" if suffix else base
            try:
                return WebsiteService.validate_slug(candidate, website)
            except SlugError:
                continue
        return None

    # ----- settings ---------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def update(website: Website, data: dict) -> Website:
        """Apply validated settings (see WebsiteUpdateSerializer)."""
        if "slug" in data:
            website.slug = WebsiteService.validate_slug(data["slug"], website) if data["slug"] else None

        if "template" in data and data["template"] != website.template:
            # Keep the candidate's visibility choices for sections the new template also has.
            hidden = {s["key"] for s in website.sections if not s["visible"]}
            website.template = data["template"]
            website.sections = [{**s, "visible": s["key"] not in hidden} for s in default_sections(website.template)]

        if "sections" in data:
            allowed = TEMPLATES[website.template]["sections"]
            given = [s for s in data["sections"] if s["key"] in allowed]
            seen = {s["key"] for s in given}
            # Sections the client didn't mention keep their place at the end, visible.
            website.sections = [*({"key": s["key"], "visible": bool(s["visible"])} for s in given),
                                *({"key": k, "visible": True} for k in allowed if k not in seen)]

        if "theme" in data:
            website.theme = {**website.theme, **data["theme"]}
        if "overrides" in data:
            website.overrides = {**website.overrides, **data["overrides"]}
        for field in ("show_chatbot", "show_matching"):
            if field in data:
                setattr(website, field, data[field])

        if "bio_text" in data:
            text = (data["bio_text"] or "").strip()
            website.bio_text = text
            # Saving is the candidate's approval (SPEC §23); record whether it started as an AI draft.
            if not text:
                website.bio_source, website.bio_approved_at = "", None
            else:
                from_ai = website.bio_draft_status == Website.DraftStatus.DONE and text == website.bio_draft_text.strip()
                website.bio_source = Website.BioSource.AI if from_ai else Website.BioSource.CANDIDATE
                website.bio_approved_at = timezone.now()

        website.save()
        return website

    # ----- rendering --------------------------------------------------------

    @staticmethod
    def build_site_data(website: Website) -> dict:
        """Everything a template needs to render the site, and nothing else.

        The single render contract for both preview and publishing: only the
        sections the candidate made visible, featured items, overrides and the
        approved bio; no internal ids, provenance or notes.
        """
        profile = CandidateProfileService.get(website.user) or {}
        overrides = website.overrides or {}
        experience = profile.get("experience", [])
        links = [_clean(link) for link in profile.get("links", [])]
        bullets = {b for e in experience for b in (e.get("responsibilities") or []) + (e.get("achievements") or [])}

        skills = _grouped_skills(profile.get("skills", []))
        known_skills = {s["name"].lower() for s in profile.get("skills", [])}
        extra_tech = sorted(
            {
                t
                for item in experience + profile.get("projects", [])
                for t in item.get("technologies") or []
                if t.lower() not in known_skills
            },
            key=str.lower,
        )

        content = {
            "about": {
                "intro": overrides.get("intro") or None,
                "text": website.bio_text if website.bio_approved_at else profile.get("summary"),
            },
            "experience": [_clean(e) for e in experience],
            "leadership": [b for b in overrides.get("leadership") or [] if b in bullets],
            "achievements": [_clean(a) for a in _featured(profile.get("achievements", []), overrides.get("featured_achievements"))],
            "highlights": [
                {"text": a, "context": _role(e)} for e in experience for a in (e.get("achievements") or [])
            ]
            + [{"text": a["title"], "context": a.get("description")} for a in profile.get("achievements", [])],
            "skills": skills,
            "tech_stack": {"groups": skills, "also_used": extra_tech},
            "projects": [_clean(p) for p in _featured(profile.get("projects", []), overrides.get("featured_projects"))],
            "github": _github(links),
            "education": [_clean(e) for e in profile.get("education", [])],
            "certifications": [_clean(c) for c in profile.get("certifications", [])],
            "contact": {
                "email": profile.get("email"),
                "phone": profile.get("phone"),
                "location": profile.get("location"),
                "links": links,
            },
        }

        def has_content(key):
            value = content[key]
            if key == "about":
                return bool(value["intro"] or value["text"])
            if key == "tech_stack":
                return bool(value["groups"] or value["also_used"])
            if key == "contact":
                return bool(value["email"] or value["phone"] or value["links"])
            return bool(value)

        allowed = TEMPLATES[website.template]["sections"]
        titles = overrides.get("titles") or {}
        sections = [
            {"key": s["key"], "title": (titles.get(s["key"]) or SECTIONS[s["key"]]).strip()}
            for s in website.sections
            if s["visible"] and s["key"] in allowed and has_content(s["key"])
        ]
        name = profile.get("full_name") or ""
        headline = profile.get("headline") or ""
        tagline = overrides.get("tagline") or ""
        description = tagline or overrides.get("intro") or (content["about"]["text"] or "")
        return {
            "version": SITE_DATA_VERSION,
            "template": website.template,
            "theme": website.theme,
            "hero": {"name": name, "headline": headline or None, "tagline": tagline or None, "location": profile.get("location")},
            "sections": sections,
            "content": {s["key"]: content[s["key"]] for s in sections},
            "widgets": {"chatbot": False, "matching": False},  # filled in for the live site (4b)
            "meta": {
                "title": " — ".join(v for v in (name, headline) if v) or "Portfolio",
                "description": description[:300],
            },
        }

    # ----- preview ----------------------------------------------------------

    @staticmethod
    def issue_preview(website: Website) -> PreviewToken:
        return PreviewToken.objects.create(website=website, expires_at=timezone.now() + PREVIEW_TTL)

    @staticmethod
    def resolve_preview(token: str, request=None) -> Website | None:
        preview = PreviewToken.objects.select_related("website__user").filter(token=token).first()
        if preview is None or preview.expires_at <= timezone.now():
            return None
        if preview.opened_at is None:
            PreviewToken.objects.filter(pk=preview.pk, opened_at=None).update(opened_at=timezone.now())
            WebsiteEvent.objects.create(
                website=preview.website,
                kind=WebsiteEvent.Kind.PREVIEW_OPENED,
                ip_hash=ip_hash(request) if request is not None else "",
            )
        return preview.website

    # ----- publishing -------------------------------------------------------

    @staticmethod
    def publish_problems(website: Website) -> list[str]:
        """Why the site can't be published yet (empty when it can). Paid checks go through entitlements."""
        from apps.payments.models import Entitlement
        from apps.payments.services import EntitlementService

        problems = []
        codes = EntitlementService.active_codes(website.user)
        if Entitlement.Code.WEBSITE_PUBLISH not in codes:
            problems.append("Unlock Pro to publish your site.")
        elif website.template in PREMIUM_TEMPLATES and Entitlement.Code.PREMIUM_TEMPLATES not in codes:
            problems.append("This template is part of Pro.")
        if not CandidateProfile.objects.filter(user=website.user).exists():
            problems.append("Save your profile first.")
        if not website.slug:
            problems.append("Choose a web address for your site.")
        if website.bio_text and not website.bio_approved_at:
            problems.append("Save (approve) your bio before publishing.")
        return problems


# Website section -> knowledge-base source types the embedded assistant may use.
SECTION_SOURCE_TYPES = {
    "about": ["profile"],
    "experience": ["experience"],
    "leadership": ["experience"],
    "highlights": ["experience", "achievement"],
    "achievements": ["achievement"],
    "skills": ["skills"],
    "tech_stack": ["skills"],
    "projects": ["project"],
    "education": ["education"],
    "certifications": ["certification"],
}
VIEW_DEDUPE_SECONDS = 3600


class PublishError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def _comparable(data: dict) -> dict:
    # Widgets are decided live on the public site, so they don't count as unpublished changes.
    return {k: v for k, v in data.items() if k != "widgets"}


class PublishingService:
    @staticmethod
    @transaction.atomic
    def publish(website: Website, request=None):
        website = Website.objects.select_for_update().get(pk=website.pk)
        problems = WebsiteService.publish_problems(website)
        if problems:
            raise PublishError(problems)
        last = website.versions.order_by("-number").first()
        version = WebsiteVersion.objects.create(
            website=website,
            number=(last.number + 1) if last else 1,
            template=website.template,
            data=WebsiteService.build_site_data(website),
        )
        website.published_version = version
        website.save(update_fields=["published_version", "updated_at"])
        WebsiteEvent.objects.create(
            website=website, kind=WebsiteEvent.Kind.PUBLISHED, ip_hash=ip_hash(request) if request is not None else ""
        )
        return version

    @staticmethod
    @transaction.atomic
    def unpublish(website: Website, request=None) -> None:
        if website.published_version_id is None:
            return
        website.published_version = None
        website.save(update_fields=["published_version", "updated_at"])
        WebsiteEvent.objects.create(
            website=website, kind=WebsiteEvent.Kind.UNPUBLISHED, ip_hash=ip_hash(request) if request is not None else ""
        )

    @staticmethod
    def status(website: Website) -> dict:
        version = website.published_version
        if version is None:
            return {"published": False, "version": None, "published_at": None, "has_changes": False, "path": None}
        return {
            "published": True,
            "version": version.number,
            "published_at": version.published_at,
            "has_changes": _comparable(WebsiteService.build_site_data(website)) != _comparable(version.data),
            "path": f"/portfolio/{website.slug}",
        }

    @staticmethod
    def resolve_public(slug: str) -> Website | None:
        """The published website at `slug`, or None (unknown, or not published)."""
        return (
            Website.objects.select_related("published_version", "user")
            .filter(slug=(slug or "").lower(), published_version__isnull=False)
            .first()
        )

    @staticmethod
    def widget_flags(website: Website) -> dict:
        """A widget shows only if the site enables it AND the candidate's global switch is on (SPEC §11)."""
        from apps.ai_profile.models import EmployerProfile

        profile = EmployerProfile.objects.filter(user=website.user).first()
        chatbot_on = profile.chatbot_enabled if profile else EmployerProfile._meta.get_field("chatbot_enabled").default
        matching_on = profile.matching_enabled if profile else EmployerProfile._meta.get_field("matching_enabled").default
        return {"chatbot": website.show_chatbot and chatbot_on, "matching": website.show_matching and matching_on}

    @staticmethod
    def public_data(website: Website, request=None) -> dict:
        data = dict(website.published_version.data)
        data["widgets"] = {
            **PublishingService.widget_flags(website),
            "slug": website.slug,
            "turnstile_site_key": settings.TURNSTILE_SITE_KEY or None,
        }
        if request is not None:
            hashed = ip_hash(request)
            if cache.add(f"site-view:{website.pk}:{hashed}", 1, timeout=VIEW_DEDUPE_SECONDS):
                WebsiteEvent.objects.create(website=website, kind=WebsiteEvent.Kind.PUBLIC_VIEW, ip_hash=hashed)
        return data

    @staticmethod
    def source_types(website: Website) -> list[str]:
        """Source types for the embedded assistant: only what the *published* site shows."""
        shown = [s["key"] for s in website.published_version.data.get("sections", [])]
        return sorted({t for key in shown for t in SECTION_SOURCE_TYPES.get(key, [])})
