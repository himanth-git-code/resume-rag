from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Local runs outside Docker can use backend/.env; Compose injects env directly.
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.headless",
    "apps.accounts",
    "apps.candidates",
    "apps.documents",
    "apps.resume_parser",
    "apps.knowledge_base",
    "apps.questions",
    "apps.ai_profile",
    "apps.chatbot",
    "apps.websites",
    "apps.payments",
    "apps.support",
    "apps.admin_portal",
    "apps.audit",
    "apps.ai",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Closed by default: public endpoints must opt in with AllowAny.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "resume_upload": env("RESUME_UPLOAD_RATE", default="20/hour"),
        "question_generate": env("QUESTION_GENERATE_RATE", default="20/hour"),
        "public_view": env("PUBLIC_VIEW_RATE", default="120/hour"),
        "public_chat": env("PUBLIC_CHAT_RATE", default="60/hour"),
        "public_match": env("PUBLIC_MATCH_RATE", default="10/hour"),
        "public_poll": env("PUBLIC_POLL_RATE", default="1500/hour"),
    },
    # Client IP for throttling = the X-Forwarded-For entry added by our outermost
    # trusted proxy: 1 locally (Next.js), 2 behind the production load balancer.
    "NUM_PROXIES": env.int("TRUSTED_PROXY_COUNT", default=1),
}

REDIS_URL = env("REDIS_URL")

# Shared cache: allauth's login/signup rate limits must be shared across processes.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# The browser reaches Django through the Next.js proxy, which sets X-Forwarded-Host
# to the public host. Needed so OAuth redirect URIs and frontend redirects point
# at the frontend origin rather than the internal backend host.
USE_X_FORWARDED_HOST = True

# Authentication (django-allauth, headless: JSON API for the Next.js SPA).
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = True
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
# Relative URLs resolve against the forwarded (frontend) host.
HEADLESS_FRONTEND_URLS = {
    "account_signup": "/signup",
    "account_reset_password": "/login",
    "account_reset_password_from_key": "/login",
    "account_confirm_email": "/login",
    "socialaccount_login_error": "/login?error=social",
}

# Google sign-in: a verified Google email logs into the account with that email.
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_PROVIDERS = {}
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")
if GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APPS": [{"client_id": GOOGLE_OAUTH_CLIENT_ID, "secret": GOOGLE_OAUTH_CLIENT_SECRET}],
        "SCOPE": ["openid", "email", "profile"],
        "AUTH_PARAMS": {"prompt": "select_account"},
        "OAUTH_PKCE_ENABLED": True,
    }

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Tasks must be idempotent: acks_late re-delivers work if a worker dies mid-task.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Private object storage for candidate documents: S3 in production, SeaweedFS
# (S3-compatible) locally. Objects are never public; access is via short-lived
# signed URLs only.
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("S3_BUCKET_NAME", default=None),
            "endpoint_url": env("S3_ENDPOINT_URL", default=None),
            "access_key": env("S3_ACCESS_KEY_ID", default=None),
            "secret_key": env("S3_SECRET_ACCESS_KEY", default=None),
            "region_name": env("S3_REGION_NAME", default="us-east-1"),
            "default_acl": "private",
            "querystring_auth": True,
            "querystring_expire": 300,
            "file_overwrite": False,
            "addressing_style": "path",
            "signature_version": "s3v4",
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Resume uploads.
RESUME_MAX_UPLOAD_MB = env.int("RESUME_MAX_UPLOAD_MB", default=5)
RESUME_MAX_PDF_PAGES = env.int("RESUME_MAX_PDF_PAGES", default=20)
DATA_UPLOAD_MAX_MEMORY_SIZE = (RESUME_MAX_UPLOAD_MB + 1) * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE

# AI provider (see apps/ai). "fake" returns canned output and needs no API key.
AI_PROVIDER = env("AI_PROVIDER", default="anthropic")
AI_MODEL = env("AI_MODEL", default="claude-opus-5")
AI_REQUEST_TIMEOUT_SECONDS = env.float("AI_REQUEST_TIMEOUT_SECONDS", default=180.0)
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")

# Embeddings for the knowledge base (see apps/ai). "fake" needs no API key but
# gives meaningless search results.
EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER", default="fake")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", default="voyage-4")
# Must match the VectorField size in apps.knowledge_base (changing it needs a migration).
EMBEDDING_DIMENSIONS = 1024
VOYAGE_API_KEY = env("VOYAGE_API_KEY", default="")

# Employer-facing AI profile (apps.ai_profile, apps.chatbot).
CHAT_MODEL = env("CHAT_MODEL", default="claude-sonnet-5")
CHAT_DAILY_LIMIT_PER_PROFILE = env.int("CHAT_DAILY_LIMIT_PER_PROFILE", default=300)
MATCH_DAILY_LIMIT_PER_PROFILE = env.int("MATCH_DAILY_LIMIT_PER_PROFILE", default=50)
# Cloudflare Turnstile bot protection on public endpoints; off when unset.
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
