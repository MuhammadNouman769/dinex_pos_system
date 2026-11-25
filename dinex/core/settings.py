"""
Django settings for core project.
MN Kitchen POS Backend
"""
from datetime import timedelta
from pathlib import Path
from decouple import config
# =============================================================================
# BASE
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY = config("SECRET_KEY")
DEBUG = config(
    "DEBUG",
    default=False,
    cast=bool,
)
if not DEBUG and (
    len(SECRET_KEY) < 40
    or SECRET_KEY.startswith(("django-insecure", "dev-", "change-me", "test-"))
):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "SECRET_KEY is missing or too weak for production. Generate one with: "
        "python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=lambda v: [h.strip() for h in v.split(",") if h.strip()],
)

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in config(
        "CORS_ALLOWED_ORIGINS",
        # development only: the Next.js dev server. In production the app and API share one domain, so this stays empty.
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",") if o.strip()
]
# =============================================================================
# CUSTOM USER
# =============================================================================
AUTH_USER_MODEL = "accounts.User"
# =============================================================================
# APPLICATIONS
# =============================================================================
INSTALLED_APPS = [
    # -------------------------------------------------------------------------
    # Django
    # -------------------------------------------------------------------------
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # -------------------------------------------------------------------------
    # Third-party
    # -------------------------------------------------------------------------
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # -------------------------------------------------------------------------
    # Local
    # -------------------------------------------------------------------------
    "apps.utils",
    "apps.accounts",
    "apps.onboarding",
    "apps.organizations",
    "apps.catalog",
    "apps.products",
    "apps.customers",
    "apps.orders",
    "apps.inventory",
    "apps.cash",
    "apps.operations",
    "apps.loyalty",
    "apps.billing",
    "apps.staff",
    "apps.payroll",
    "apps.analytics",
    "apps.reports",
]
# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'apps.utils.middleware.OrganizationMiddleware',
]
# =============================================================================
# URL / WSGI / ASGI
# =============================================================================
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"
# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),
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
# =============================================================================
# DATABASE
# =============================================================================
def _database_from_url(url):
    """postgres://user:pass@host:5432/dbname  (or  ...@/dbname?host=/path/to/socket)"""
    from urllib.parse import parse_qs, unquote, urlparse
    u = urlparse(url)
    if u.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL must start with postgres:// or postgresql://")
    query = parse_qs(u.query)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(u.path.lstrip("/")),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": query.get("host", [u.hostname or ""])[0],
        "PORT": str(u.port or ""),
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
        "OPTIONS": {"connect_timeout": 10},
    }


DATABASE_URL = config("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
else:
    # Local development: SQLite (set DATABASE_URL to use PostgreSQL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / config("DB_NAME", default="db.sqlite3"),
        }
    }
# =============================================================================
# PASSWORD VALIDATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]
# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = True
# =============================================================================
# STATIC FILES
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = Path(config("STATIC_ROOT", default=str(BASE_DIR / "staticfiles")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# =============================================================================
# MEDIA FILES
# =============================================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(BASE_DIR / "media")))
# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    # -------------------------------------------------------------------------
    # OpenAPI
    # -------------------------------------------------------------------------
    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
    ),
    # -------------------------------------------------------------------------
    # JWT Authentication
    # -------------------------------------------------------------------------
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.billing.auth.SubscriptionAwareJWTAuthentication",
    ),
    # -------------------------------------------------------------------------
    # Default Permission
    # -------------------------------------------------------------------------
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # -------------------------------------------------------------------------
    # Pagination
    # -------------------------------------------------------------------------
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 20,
    # -------------------------------------------------------------------------
    # Brute-force protection (login) - counters are per server process
    # -------------------------------------------------------------------------
    "DEFAULT_THROTTLE_RATES": {"login": config("LOGIN_RATE", default="30/min"), "kiosk": config("KIOSK_RATE", default="120/min"), "signup": config("SIGNUP_RATE", default="10/hour")},
    "NUM_PROXIES": config("NUM_PROXIES", default=1, cast=int),   # Caddy / nginx in front
}
# =============================================================================
# SIMPLE JWT
# =============================================================================
SIMPLE_JWT = {
    # -------------------------------------------------------------------------
    # Access Token
    # -------------------------------------------------------------------------
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config(
            "JWT_ACCESS_TOKEN_MINUTES",
            default=30,
            cast=int,
        )
    ),
    # -------------------------------------------------------------------------
    # Refresh Token
    # -------------------------------------------------------------------------
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config(
            "JWT_REFRESH_TOKEN_DAYS",
            default=7,
            cast=int,
        )
    ),
    # -------------------------------------------------------------------------
    # Refresh Token Rotation
    # -------------------------------------------------------------------------
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # -------------------------------------------------------------------------
    # Authentication Header
    # -------------------------------------------------------------------------
    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),
    # -------------------------------------------------------------------------
    # Update Last Login
    # -------------------------------------------------------------------------
    "UPDATE_LAST_LOGIN": True,
}
# =============================================================================
# DRF SPECTACULAR / SWAGGER
# =============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "The MN Kitchen POS API",
    "DESCRIPTION": (
        "REST API for The MN Kitchen POS "
        "restaurant management and "
        "point-of-sale system."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # -------------------------------------------------------------------------
    # API Tags
    # -------------------------------------------------------------------------
    "TAGS": [
        {
            "name": "Authentication",
            "description": (
                "Platform authentication and JWT"
            ),
        },
        {
            "name": "Onboarding",
            "description": (
                "First-time restaurant setup"
            ),
        },
        {
            "name": "Organizations",
            "description": (
                "Organization management"
            ),
        },
        {
            "name": "Products",
            "description": (
                "Products and categories"
            ),
        },
        {
            "name": "Customers",
            "description": (
                "Customer management"
            ),
        },
        {
            "name": "Orders",
            "description": (
                "Order management"
            ),
        },
        {
            "name": "Inventory",
            "description": (
                "Inventory management"
            ),
        },
       {
            "name": "Reports",
            "description": (
                "Reports and analytics"
            ),
        },
    ],
}
# =============================================================================
# EMAIL
# =============================================================================
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.console.EmailBackend"
    ),
)
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="DineX <no-reply@dinex.local>")
# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)

# ----------------------------------------------------------------------------
# Billing (XverLabs subscriptions)
# ----------------------------------------------------------------------------
TERMS_VERSION = config("TERMS_VERSION", default="2026-11")
BILLING_TRIAL_DAYS = config("BILLING_TRIAL_DAYS", default=14, cast=int)
BILLING_INVOICE_DUE_DAYS = config("BILLING_INVOICE_DUE_DAYS", default=7, cast=int)
BILLING_GRACE_DAYS = config("BILLING_GRACE_DAYS", default=7, cast=int)   # overdue this long -> suspended


# ----------------------------------------------------------------------------
# Production security (active whenever DEBUG is off)
# ----------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="",
    cast=lambda v: [o.strip() for o in v.split(",") if o.strip()],
)
DJANGO_ADMIN_URL = config("DJANGO_ADMIN_URL", default="django-admin/")
ENABLE_API_DOCS = config("ENABLE_API_DOCS", default=DEBUG, cast=bool)

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # TLS ends at the proxy
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]                  # container health check is plain http
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
    "loggers": {"django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}

# Advisory checks we deliberately do not follow:
#  - security.W005/W021: HSTS for subdomains / preload list (a restaurant may later get its own subdomain or domain)
#  - drf_spectacular.W001/W002: API docs are switched off in production
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021", "drf_spectacular.W001", "drf_spectacular.W002"]
