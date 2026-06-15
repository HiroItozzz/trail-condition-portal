from .base import *

if "K_SERVICE" in os.environ:
    raise RuntimeError("本番環境で開発用設定が読み込まれました")

# ======================================================

ALLOWED_HOSTS = [
    ".localhost",
    "127.0.0.1",
    ".192.168.40.197",
]
ALLOWED_HOSTS += [h for h in os.environ.get("EXTRA_ALLOWED_HOSTS", "").split(",") if h]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ログファイル出力設定
if DEBUG:
    LOGGING["handlers"]["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": BASE_DIR / "logs" / "django.log",
        "maxBytes": 5 * 1024 * 1024,  # 5MB
        "backupCount": 5,
        "formatter": "verbose",
    }
    LOGGING["loggers"]["django"]["handlers"].append("file")
    LOGGING["loggers"]["trail_status"]["handlers"].append("file")
    LOGGING["loggers"]["trail_status"]["level"] = "DEBUG"


# テンプレート設定
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "string_if_invalid": "存在しない変数: %s",
        },
    },
]
