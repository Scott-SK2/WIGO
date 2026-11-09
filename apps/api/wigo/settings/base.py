"""
Réglages communs WIGO. Les secrets viennent de l'environnement (voir .env.example).
Référence : cahier des charges v1.2, §8 (architecture et sécurité).
"""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
    DATABASE_URL=(str, "postgis://wigo:wigo@localhost:5432/wigo"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    EMAIL_URL=(str, "consolemail://"),
    PUBLIC_WEB_URL=(str, "http://localhost:3000"),
    MEDIA_BACKEND=(str, "local"),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
PUBLIC_WEB_URL = env("PUBLIC_WEB_URL")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django.contrib.postgres",
    # tiers
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    # WIGO
    "core",
    "accounts",
    "organizations",
    "catalog",
    "events",
    "moderation",
    "engagement",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wigo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "wigo.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
DATABASES["default"]["CONN_MAX_AGE"] = 60

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# i18n : FR / NL / EN, dates en UTC, fuseau métier Europe/Brussels (RG-19)
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("nl", "Nederlands"), ("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
WIGO_DEFAULT_TIMEZONE = "Europe/Brussels"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if env("MEDIA_BACKEND") == "r2":  # Cloudflare R2 (compatible S3) — §8.1 Médias
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("R2_BUCKET"),
            "endpoint_url": f"https://{env('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
            "access_key": env("R2_ACCESS_KEY_ID"),
            "secret_key": env("R2_SECRET_ACCESS_KEY"),
            "region_name": "auto",
            "default_acl": None,
            "querystring_auth": False,
        },
    }

# Uploads limités en taille et type (§5.3)
WIGO_MAX_UPLOAD_BYTES = 8 * 1024 * 1024
WIGO_ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
DATA_UPLOAD_MAX_MEMORY_SIZE = WIGO_MAX_UPLOAD_BYTES

# E-mails
vars().update(env.email_url("EMAIL_URL"))
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="WIGO <no-reply@wigo.be>")

# Sécurité (§8.2)
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.CursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "core.exceptions.exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "300/min",
        "user": "600/min",
        "auth": "10/min",
        "newsletter": "5/hour",
        "report": "20/hour",
        "submit": "30/day",
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    # « format » est un filtre métier (présentiel / en ligne), pas un suffixe de rendu DRF
    "URL_FORMAT_OVERRIDE": None,
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

# Jetons courts, rotation et révocation (§8.2)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "WIGO API",
    "DESCRIPTION": "API publique et organisateurs de WIGO — Trouve ta prochaine sortie.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "EventStatusEnum": "events.models.EventStatus",
        "OccurrenceStatusEnum": "events.models.OccurrenceStatus",
        "TrustLevelEnum": "core.enums.TrustLevel",
    },
}

# Celery (§8.1 Asynchrone)
CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TIMEZONE = "Europe/Brussels"
CELERY_BEAT_SCHEDULE = {
    "archive-finished-events": {
        "task": "events.tasks.archive_finished_events",
        "schedule": 60 * 60,  # toutes les heures
    },
    "freshness-reminders": {
        "task": "events.tasks.send_freshness_reminders",
        "schedule": 60 * 60,
    },
    "weekly-newsletter": {
        # jeudi 10h Europe/Brussels — « Ce week-end à Bruxelles »
        "task": "engagement.tasks.send_weekly_newsletter",
        "schedule": crontab(hour=10, minute=0, day_of_week=4),
    },
}

# Règles métier paramétrables (§5.4, annexe A)
WIGO_RULES = {
    "NEW_ACCOUNT_DAILY_SUBMISSIONS": 10,  # quota anti-spam compte Nouveau
    "CONFIRMED_AFTER_APPROVED_EVENTS": 3,  # Nouveau -> Confirmé
    "LONG_EVENT_DAYS": 3,  # RG-23
    "MAJOR_CHANGE_TIME_SHIFT_HOURS": 2,  # annexe A.2
    "FRESHNESS_REMINDER_HOURS": 72,  # §5.7
    "SUSPENSION_REPORTS": 2,  # annexe A.3
    "SUSPENSION_WINDOW_DAYS": 30,
    "SUSPENSION_DURATION_DAYS": 7,
    "EMAIL_TOKEN_TTL_HOURS": 48,
    "PASSWORD_TOKEN_TTL_HOURS": 2,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
            '"message":"%(message)s"}'
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
