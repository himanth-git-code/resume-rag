from django.contrib import admin
from django.urls import include, path

from config.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/", include("apps.candidates.urls")),
    path("api/", include("apps.resume_parser.urls")),
    # Headless auth API for the SPA (login, signup, session, social redirect).
    path("_allauth/", include("allauth.headless.urls")),
    # Browser-facing allauth routes; needed for the OAuth provider callback.
    path("accounts/", include("allauth.urls")),
]
