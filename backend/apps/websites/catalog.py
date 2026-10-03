"""Website templates, sections and themes (SPEC §11).

Templates are data: each is a name plus the sections it supports, in their
default order. The rendering lives in the frontend's server-side template
components, which read this same structure from `SiteData`.
"""

# Section key -> default heading.
SECTIONS = {
    "about": "About",
    "experience": "Experience",
    "leadership": "Leadership",
    "achievements": "Achievements",
    "highlights": "Technical highlights",
    "skills": "Skills",
    "tech_stack": "Technology stack",
    "projects": "Projects",
    "github": "GitHub",
    "education": "Education",
    "certifications": "Certifications",
    "contact": "Contact",
}

TEMPLATES = {
    "executive": {
        "name": "Executive",
        "description": "Calm, authoritative layout for managers, executives and consultants.",
        "sections": ["about", "experience", "leadership", "achievements", "skills", "education", "contact"],
    },
    "modern": {
        "name": "Modern Professional",
        "description": "Balanced, card-based layout that suits most professionals.",
        "sections": ["about", "experience", "skills", "projects", "certifications", "contact"],
    },
    "technical": {
        "name": "Technical",
        "description": "For engineers and architects: stack, projects and technical highlights first.",
        "sections": ["about", "tech_stack", "projects", "highlights", "experience", "github", "certifications", "contact"],
    },
    "creative": {
        "name": "Creative",
        "description": "Large typography and a visual project grid for designers and creatives.",
        "sections": ["projects", "about", "experience", "skills", "contact"],
    },
    "minimal": {
        "name": "Minimal",
        "description": "Clean single column: just the essentials.",
        "sections": ["about", "experience", "skills", "projects", "education", "contact"],
    },
}
DEFAULT_TEMPLATE = "modern"
# Default Pro templates; admins can change this in the template catalog (TemplateSetting).
PREMIUM_TEMPLATES = {"executive", "technical", "creative"}

PALETTES = {
    "slate": "Slate",
    "ocean": "Ocean",
    "forest": "Forest",
    "plum": "Plum",
    "amber": "Amber",
    "rose": "Rose",
}
MODES = ("light", "dark")
FONTS = {
    "inter": "Inter",
    "serif": "Playfair Display + Source Sans",
    "grotesk": "Space Grotesk + Inter",
    "classic": "Merriweather + Lato",
}
DEFAULT_THEME = {"palette": "slate", "mode": "light", "font": "inter"}

SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])$"
RESERVED_SLUGS = {
    "about", "admin", "api", "app", "assets", "contact", "dashboard", "edit", "help", "login", "logout",
    "me", "new", "portfolio", "preview", "privacy", "settings", "signup", "static", "support", "terms", "www",
}


def effective_templates() -> dict[str, dict]:
    """Code-defined templates with the admin's catalog settings applied.

    `supported` is what the code can render; `sections` is the admin's default
    order for new sites (a subset of `supported`).
    """
    from .models import TemplateSetting  # catalog <-> models import cycle

    settings_by_key = {s.key: s for s in TemplateSetting.objects.all()}
    result = {}
    for key, base in TEMPLATES.items():
        s = settings_by_key.get(key)
        defaults = [k for k in (s.default_sections if s and s.default_sections else base["sections"]) if k in base["sections"]]
        result[key] = {
            "name": s.name if s else base["name"],
            "description": s.description if s else base["description"],
            "enabled": s.enabled if s else True,
            "premium": s.premium if s else key in PREMIUM_TEMPLATES,
            "sections": defaults or list(base["sections"]),
            "supported": list(base["sections"]),
        }
    return result


def is_premium(template: str) -> bool:
    return effective_templates().get(template, {}).get("premium", False)


def is_enabled(template: str) -> bool:
    return effective_templates().get(template, {}).get("enabled", False)


def default_sections(template: str) -> list[dict]:
    try:
        keys = effective_templates()[template]["sections"]
    except Exception:  # e.g. before migrations exist
        keys = TEMPLATES[template]["sections"]
    return [{"key": key, "visible": True} for key in keys]


def catalog() -> dict:
    """What the candidate's editor offers: enabled templates only."""
    templates = effective_templates()
    return {
        "templates": [
            {"key": k, "name": v["name"], "description": v["description"], "sections": v["sections"], "premium": v["premium"]}
            for k, v in templates.items()
            if v["enabled"]
        ],
        "sections": SECTIONS,
        "palettes": [{"key": k, "name": v} for k, v in PALETTES.items()],
        "modes": list(MODES),
        "fonts": [{"key": k, "name": v} for k, v in FONTS.items()],
    }
