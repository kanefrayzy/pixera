# FILE: ai_gallery/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

# ── helpers ───────────────────────────────────────────────────────────────────
def env_bool(name: str, default: bool = False) -> bool:
    v = str(os.getenv(name, str(int(default)))).strip().lower()
    return v in {"1", "true", "yes", "y", "on"}

def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def env_required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ImproperlyConfigured(f"Environment variable {name} is required")
    return val

# ── base ──────────────────────────────────────────────────────────────────────
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-prod")
DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000",
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = env_int("SITE_ID", 1)

# URL configuration
APPEND_SLASH = False

# ── i18n ──────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "ru")
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", _("English")),
    ("es", _("Spanish")),
    ("pt", _("Portuguese")),
    ("de", _("German")),
    ("ru", _("Russian")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = os.getenv("LANGUAGE_COOKIE_NAME", "django_language")
LANGUAGE_COOKIE_AGE = env_int("LANGUAGE_COOKIE_AGE", 60 * 60 * 24 * 365 * 5)  # 5 лет
LANGUAGE_COOKIE_SAMESITE = os.getenv("LANGUAGE_COOKIE_SAMESITE", "Lax")
LANGUAGE_COOKIE_SECURE = not DEBUG

# ── feature flags ─────────────────────────────────────────────────────────────
FREE_FOR_STAFF = env_bool("FREE_FOR_STAFF", True)
ENABLE_DEVICE_FP = env_bool("ENABLE_DEVICE_FP", True)   # ВКЛЮЧЕНО
ENABLE_ANTIABUSE = env_bool("ENABLE_ANTIABUSE", True)   # ВКЛЮЧЕНО
ENABLE_DRF_THROTTLE = env_bool("ENABLE_DRF_THROTTLE", True)
AGE_GATE_ENABLED = env_bool("AGE_GATE_ENABLED", False)
# Allow skipping token checks and charges in local dev (DEBUG)
# ВАЖНО: Установлено False чтобы токены списывались даже в режиме разработки
ALLOW_FREE_LOCAL_VIDEO = env_bool("ALLOW_FREE_LOCAL_VIDEO", False)

# ── apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",

    "rest_framework",
    "django_filters",
    "channels",
    "django_celery_beat",

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.discord",

    "pages",
    "dashboard.apps.DashboardConfig",
    "gallery.apps.GalleryConfig",
    "moderation",
    "generate.apps.GenerateConfig",
    "blog.apps.BlogConfig",
]

# ── middleware (ПОРЯДОК ВАЖЕН) ────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",  # Сжатие ответов

    # Catch SessionInterrupted and gracefully recover on GET
    "ai_gallery.middleware.SessionRescueMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    # Отпечаток устройства и стойкие cookies (gid/fp)
    "ai_gallery.middleware.DeviceFingerprintMiddleware",

    # Мягкий анти-абуз щит (считает попытки для submit эндпоинта)
    "ai_gallery.middleware.AntiAbuseShieldMiddleware",

    # Роутинг языкового префикса (до LocaleMiddleware)
    "ai_gallery.middleware.LanguagePrefixRedirectMiddleware",

    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",

    # Отключение CSRF для webhook endpoints (должен быть ДО CsrfViewMiddleware)
    "ai_gallery.middleware.DisableCSRFMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Плашка 18+
    "ai_gallery.middleware.AgeGateMiddleware",
]

# Если флаги отключены через env — динамически уберём прослойки
if not ENABLE_DEVICE_FP and "ai_gallery.middleware.DeviceFingerprintMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("ai_gallery.middleware.DeviceFingerprintMiddleware")
if not ENABLE_ANTIABUSE and "ai_gallery.middleware.AntiAbuseShieldMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("ai_gallery.middleware.AntiAbuseShieldMiddleware")
if not AGE_GATE_ENABLED and "ai_gallery.middleware.AgeGateMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("ai_gallery.middleware.AgeGateMiddleware")

ROOT_URLCONF = "ai_gallery.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "gallery.context_processors.nav_context",
                "ai_gallery.context_processors.auth_flags",
                "dashboard.context_processors.wallet_context",
                "dashboard.context_processors.user_profile",
                "dashboard.context_processors.follow_stats",
                "pages.context_processors.site_settings",
            ],
        },
    }
]

WSGI_APPLICATION = "ai_gallery.wsgi.application"
ASGI_APPLICATION = "ai_gallery.asgi.application"

# ── Channels (WebSocket) ──────────────────────────────────────────────────────
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# ── database (PostgreSQL в продакшн, SQLite в dev) ──────────────────────────
if DEBUG:
    # Development: SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 30
            },
        }
    }
else:
    # Production: PostgreSQL
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "pixera"),
            "USER": os.getenv("POSTGRES_USER", "pixera_user"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

# ── auth (allauth) ────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/dashboard/me"
ACCOUNT_SIGNUP_REDIRECT_URL = LOGIN_REDIRECT_URL
ACCOUNT_ADAPTER = "ai_gallery.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "ai_gallery.adapters.SocialAccountAdapter"
LOGOUT_REDIRECT_URL = "pages:home"

ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "optional")
ACCOUNT_SESSION_REMEMBER = None
ACCOUNT_RATE_LIMITS = {"login_failed": os.getenv("ACCOUNT_RATE_LIMIT_LOGIN_FAILED", "5/5m")}
ACCOUNT_LOGIN_ON_SIGNUP = True

# Настройки для социальных аккаунтов
SOCIALACCOUNT_AUTO_SIGNUP = True  # Автоматическая регистрация без формы
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # Использовать email для аутентификации
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # Автоматически связывать по email
SOCIALACCOUNT_QUERY_EMAIL = True  # Запрашивать email, если не получен

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "facebook": {
        "SCOPE": ["email", "public_profile"],
        "AUTH_PARAMS": {},
        "FIELDS": ["id", "email", "name", "first_name", "last_name"],
    },
    "discord": {
        "SCOPE": ["identify", "email"],
        "AUTH_PARAMS": {},
    },
}
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["google"]["APP"] = {
        "client_id": GOOGLE_CLIENT_ID,
        "secret": GOOGLE_CLIENT_SECRET,
        "key": "",
    }

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
if FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["facebook"]["APP"] = {
        "client_id": FACEBOOK_CLIENT_ID,
        "secret": FACEBOOK_CLIENT_SECRET,
        "key": "",
    }

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
if DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["discord"]["APP"] = {
        "client_id": DISCORD_CLIENT_ID,
        "secret": DISCORD_CLIENT_SECRET,
        "key": "",
    }

# ── static & media ────────────────────────────────────────────────────────────
import time
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Auto-generate version based on current timestamp for cache busting
STATIC_VERSION = str(int(time.time()))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_MAX_AGE = 31536000

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Video tools
# Path to ffmpeg binary for video compression. Override via env if needed.
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")

# ── dev proxy / ngrok ─────────────────────────────────────────────────────────
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")
if NGROK_DOMAIN:
    ALLOWED_HOSTS += [NGROK_DOMAIN]
    CSRF_TRUSTED_ORIGINS += [f"https://{NGROK_DOMAIN}", f"http://{NGROK_DOMAIN}"]
else:
    ALLOWED_HOSTS += [".ngrok-free.app"]
    CSRF_TRUSTED_ORIGINS += ["https://*.ngrok-free.app", "http://*.ngrok-free.app"]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── caching ───────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ai-gallery-cache",
        "TIMEOUT": 60 * 60,
    }
}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
}
if ENABLE_DRF_THROTTLE:
    REST_FRAMEWORK.update(
        {
            "DEFAULT_THROTTLE_CLASSES": [
                "rest_framework.throttling.AnonRateThrottle",
                "rest_framework.throttling.UserRateThrottle",
            ],
            "DEFAULT_THROTTLE_RATES": {
                "anon": os.getenv("DRF_THROTTLE_ANON", "60/min"),
                "user": os.getenv("DRF_THROTTLE_USER", "120/min"),
            },
        }
    )

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Pixera <no-reply@pixera.com>")

# ── Security ──────────────────────────────────────────────────────────────────
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_AGE = env_int("SESSION_COOKIE_AGE", 60 * 60 * 24 * 60)  # 60 дней
SESSION_SAVE_EVERY_REQUEST = env_bool("SESSION_SAVE_EVERY_REQUEST", False)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"std": {"format": "[%(levelname)s] %(asctime)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "generate.services.runware": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "generate.tasks": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# ── Celery ────────────────────────────────────────────────────────────────────
USE_CELERY = env_bool("USE_CELERY", False)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "memory://")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "cache+memory://")

# ЗАКОММЕНТИРОВАНО: Разрешаем Celery в режиме DEBUG для разработки
# if DEBUG:
#     USE_CELERY = False
#     CELERY_BROKER_URL = "memory://"
#     CELERY_RESULT_BACKEND = "cache+memory://"

# Режим для разработки / продакшена:
# - при USE_CELERY=False или memory:// задачи выполняются синхронно (ALWAYS_EAGER=True)
# - при USE_CELERY=True и Redis — задачи идут в Celery/Redis через worker
CELERY_TASK_ALWAYS_EAGER = True if (not USE_CELERY or CELERY_BROKER_URL.startswith("memory")) else False
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXPIRES = 3600
CELERY_TASK_TIME_LIMIT = 480
CELERY_TASK_SOFT_TIME_LIMIT = 420
CELERY_WORKER_DISABLE_RATE_LIMITS = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 3600, "max_connections": 5000}

CELERY_QUEUE_SUBMIT = os.getenv("CELERY_QUEUE_SUBMIT", "runware_submit")
CELERY_TASK_DEFAULT_QUEUE = CELERY_QUEUE_SUBMIT
CELERY_TASK_ROUTES = {
    "generate.tasks.run_generation_async": {"queue": CELERY_QUEUE_SUBMIT},
    "generate.tasks.poll_runware_result": {"queue": CELERY_QUEUE_SUBMIT},
    "generate.tasks.process_video_generation_async": {"queue": CELERY_QUEUE_SUBMIT},
    "generate.tasks.poll_video_result": {"queue": CELERY_QUEUE_SUBMIT},
}

# Celery Beat расписание для периодических задач
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'delete-old-unpublished-jobs': {
        'task': 'generate.tasks.delete_old_unpublished_jobs',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00 ночи
    },
}

# ── Runware ───────────────────────────────────────────────────────────────────
RUNWARE_API_URL = os.getenv("RUNWARE_API_URL", "https://api.runware.ai/v1")
RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY", "")
RUNWARE_DEFAULT_MODEL = os.getenv("RUNWARE_DEFAULT_MODEL", "runware:101@1")

_allowed_models_raw = os.getenv("RUNWARE_ALLOWED_MODELS", RUNWARE_DEFAULT_MODEL)
RUNWARE_ALLOWED_MODELS = [m.strip() for m in _allowed_models_raw.split(",") if m.strip()]
if RUNWARE_DEFAULT_MODEL not in RUNWARE_ALLOWED_MODELS:
    RUNWARE_ALLOWED_MODELS.append(RUNWARE_DEFAULT_MODEL)

RUNWARE_CHECK_NSFW = env_bool("RUNWARE_CHECK_NSFW", True)
RUNWARE_CONNECT_TIMEOUT = env_int("RUNWARE_CONNECT_TIMEOUT", 15)
RUNWARE_READ_TIMEOUT = env_int("RUNWARE_READ_TIMEOUT", 300)
RUNWARE_DOWNLOAD_TIMEOUT = env_int("RUNWARE_DOWNLOAD_TIMEOUT", 300)

RUNWARE_FORCE_SYNC = env_bool("RUNWARE_FORCE_SYNC", True)
RUNWARE_FIRST_POLL_DELAY = env_int("RUNWARE_FIRST_POLL_DELAY", 5)
RUNWARE_STUCK_TIMEOUT_SEC = env_int("RUNWARE_STUCK_TIMEOUT_SEC", 90)
RUNWARE_FALLBACK_WIDTH = env_int("RUNWARE_FALLBACK_WIDTH", 768)
RUNWARE_FALLBACK_HEIGHT = env_int("RUNWARE_FALLBACK_HEIGHT", 768)

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
RUNWARE_WEBHOOK_TOKEN = os.getenv("RUNWARE_WEBHOOK_TOKEN", "dev_local_webhook_token")
RUNWARE_DEMO_IF_UNAUTHORIZED = env_bool("RUNWARE_DEMO_IF_UNAUTHORIZED", True)

# ── Tokens / guest / UI ───────────────────────────────────────────────────────
TOKEN_COST_PER_GEN = env_int("TOKEN_COST_PER_GEN", 10)
TOKENS_PRICE_PER_GEN = env_int("TOKENS_PRICE_PER_GEN", 10)
GUEST_INITIAL_TOKENS = env_int("GUEST_INITIAL_TOKENS", 30)
GUEST_INITIAL_JOBS = env_int("GUEST_INITIAL_JOBS", 3)
DEFAULT_THEME = os.getenv("DEFAULT_THEME", "dark")

# Как привязывать гостя к «кошельку/гранту»: "fp" (по отпечатку) или "gid"
GUEST_WALLET_BINDING = os.getenv("GUEST_WALLET_BINDING", "fp")

# Имена/каналы отпечатка для фронта/бека
FP_COOKIE_NAME = os.getenv("FP_COOKIE_NAME", "aid_fp")
FP_HEADER_NAME = os.getenv("FP_HEADER_NAME", "X-Device-Fingerprint")
FP_PARAM_NAME  = os.getenv("FP_PARAM_NAME",  "fp")

SUPPORT_TELEGRAM_URL = os.getenv("SUPPORT_TELEGRAM_URL", "https://t.me/your_support")
TELEGRAM_SUPPORT_URL = os.getenv("TELEGRAM_SUPPORT_URL", "https://t.me/your_support_handle")

# ── DeepL Translate ───────────────────────────────────────────────────────────
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
