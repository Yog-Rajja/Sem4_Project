"""Django settings for the Smart Companion backend."""

from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env if present. Never commit this file.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# The fallback is development-only and deliberately long enough to clear the
# 32-byte HMAC minimum SimpleJWT warns about. Always set DJANGO_SECRET_KEY.
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "dev-only-insecure-key-change-me-before-you-deploy-anywhere-real",
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    # Local
    "apps.accounts",
    "apps.goals",
    "apps.analytics",
    "apps.vault",
    "apps.focus",
    "apps.insights",
    "apps.studio",
    "apps.notifications",
    "apps.skillmap",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database -------------------------------------------------------------
# PostgreSQL when DB_ENGINE=postgres and a server is reachable, otherwise SQLite.
# Both go through the Django ORM natively; no third-party ODM.
if os.getenv("DB_ENGINE", "sqlite").strip().lower() in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "smart_companion"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF / JWT ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.DefaultPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- CORS -----------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

# --- AI / external services ----------------------------------------------
# Provider is swappable: see apps/goals/services/llm.py
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

# NOTE: Groq and Grok are different companies.
#   groq → api.groq.com, fast inference of open models
#   xai  → api.x.ai, Grok
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# Tried in order; a model that is exhausted (429), retired (404) or overloaded
# (503) falls through to the next. Entries with no API key are skipped, so
# listing providers you haven't signed up for costs nothing.
LLM_FALLBACK_CHAIN = os.getenv(
    "LLM_FALLBACK_CHAIN",
    ",".join(
        [
            "gemini:gemini-3.5-flash",
            "gemini:gemini-flash-latest",
            "gemini:gemini-3.5-flash-lite",
            "gemini:gemini-flash-lite-latest",
            "gemini:gemini-3.1-flash-lite",
            "groq:llama-3.3-70b-versatile",
            "openrouter:meta-llama/llama-3.3-70b-instruct:free",
            "xai:grok-3-mini",
        ]
    ),
).strip()

# Image generation is a separate, paid-tier model on Gemini. See
# apps/studio/services/imagegen.py.
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# When true, roadmap generation uses a local deterministic stub instead of a real
# LLM call. Useful for offline development; must be false for the real demo.
USE_MOCK_AI = env_bool("USE_MOCK_AI", False)

LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))

# --- Notifications --------------------------------------------------------
# Where the app is reachable, used for links inside notifications.
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")

# Web push. Generate a pair with: manage.py generate_vapid_keys
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CONTACT_EMAIL = os.getenv("VAPID_CONTACT_EMAIL", "admin@example.com")

# Email. Without EMAIL_HOST_USER, mail is printed to the console instead of
# sent — so the feature is developable with no mailbox at all.
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()

# Google displays app passwords in four spaced groups ("abcd efgh ijkl mnop").
# Pasted verbatim those spaces make SMTP auth fail with a misleading
# "username and password not accepted", so strip whitespace here rather than
# making every user work it out.
EMAIL_HOST_PASSWORD = "".join(os.getenv("EMAIL_HOST_PASSWORD", "").split())

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "Smart Companion <noreply@example.com>"
)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))

# With no mailbox configured, mail is printed to the console rather than sent —
# so the feature is developable end to end without credentials.
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else "django.core.mail.backends.console.EmailBackend"
)

# Keeps expected service-layer warnings out of the test output; the suite
# asserts on behaviour, not log lines.
TEST_RUNNER = "common.testing.QuietTestRunner"
