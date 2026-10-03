"""Admin management of the template catalog: settings, version history and restore."""

from django.db import transaction
from django.db.models import Count

from apps.audit.services import record

from .catalog import TEMPLATES, effective_templates
from .models import TemplateCatalogVersion, TemplateSetting, Website


class CatalogError(Exception):
    pass


class TemplateCatalogService:
    @staticmethod
    def list() -> list[dict]:
        usage = dict(Website.objects.values_list("template").annotate(n=Count("id")))
        published = dict(
            Website.objects.filter(published_version__isnull=False).values_list("template").annotate(n=Count("id"))
        )
        return [
            {"key": key, **data, "sites": usage.get(key, 0), "published_sites": published.get(key, 0)}
            for key, data in effective_templates().items()
        ]

    @staticmethod
    def _snapshot() -> dict:
        return {
            key: {k: v for k, v in data.items() if k != "supported"} for key, data in effective_templates().items()
        }

    @staticmethod
    def _save_version(admin, note: str) -> TemplateCatalogVersion:
        last = TemplateCatalogVersion.objects.order_by("-number").first()
        return TemplateCatalogVersion.objects.create(
            number=(last.number + 1) if last else 1, data=TemplateCatalogService._snapshot(), changed_by=admin, note=note[:200]
        )

    @staticmethod
    def _apply(key: str, values: dict) -> None:
        base = TEMPLATES[key]
        current = effective_templates()[key]
        sections = values.get("default_sections", current["sections"])
        unknown = [s for s in sections if s not in base["sections"]]
        if unknown or not sections:
            raise CatalogError(f"Sections must be a non-empty subset of: {', '.join(base['sections'])}.")
        TemplateSetting.objects.update_or_create(
            key=key,
            defaults={
                "enabled": values.get("enabled", current["enabled"]),
                "premium": values.get("premium", current["premium"]),
                "name": (values.get("name") or current["name"]).strip()[:60],
                "description": (values.get("description", current["description"]) or "").strip()[:300],
                "default_sections": list(dict.fromkeys(sections)),
            },
        )

    @staticmethod
    @transaction.atomic
    def update(admin, key: str, values: dict, request=None) -> TemplateCatalogVersion:
        if key not in TEMPLATES:
            raise CatalogError("Unknown template.")
        TemplateCatalogService._apply(key, values)
        if not any(t["enabled"] for t in effective_templates().values()):
            raise CatalogError("At least one template must stay enabled.")
        version = TemplateCatalogService._save_version(admin, f"Updated {key}")
        record("admin.template_updated", actor=admin, request=request, template=key, version=version.number,
               changes=sorted(values))
        return version

    @staticmethod
    @transaction.atomic
    def restore(admin, number: int, request=None) -> TemplateCatalogVersion:
        target = TemplateCatalogVersion.objects.filter(number=number).first()
        if target is None:
            raise CatalogError("Unknown version.")
        for key, values in target.data.items():
            if key in TEMPLATES:  # templates removed from code since are skipped
                TemplateCatalogService._apply(key, {**values, "default_sections": values.get("sections")})
        version = TemplateCatalogService._save_version(admin, f"Restored version {number}")
        record("admin.template_catalog_restored", actor=admin, request=request, restored=number, version=version.number)
        return version
