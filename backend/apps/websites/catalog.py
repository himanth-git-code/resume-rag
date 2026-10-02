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
# Publishing with these needs the `premium_templates` entitlement (editing and preview are free).
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


def default_sections(template: str) -> list[dict]:
    return [{"key": key, "visible": True} for key in TEMPLATES[template]["sections"]]


def catalog() -> dict:
    return {
        "templates": [{"key": k, **v, "premium": k in PREMIUM_TEMPLATES} for k, v in TEMPLATES.items()],
        "sections": SECTIONS,
        "palettes": [{"key": k, "name": v} for k, v in PALETTES.items()],
        "modes": list(MODES),
        "fonts": [{"key": k, "name": v} for k, v in FONTS.items()],
    }
