import os
from pathlib import Path

import dj_database_url

# 環境判定
IS_PRODUCTION = os.environ.get("IS_PRODUCTION") == "True"
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
IS_IDX = os.environ.get("IS_IDX") == "True"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if IS_PRODUCTION and DEBUG:
    raise ValueError("本番環境で DEBUG=True は許可されていません")

if IS_PRODUCTION and IS_IDX:
    raise ValueError("本番環境で IS_IDX=True は許可されていません")

if IS_PRODUCTION and (not SECRET_KEY or "insecure" in SECRET_KEY):
    raise ValueError("本番環境用のSECRET_KEYを設定してください。")

# ベースディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# インストールするアプリ
INSTALLED_APPS = [
    "django.contrib.admin",  # 管理サイト
    "django.contrib.auth",  # 認証システム
    "django.contrib.contenttypes",  # コンテンツタイプフレームワーク
    "django.contrib.sessions",  # セッションフレームワーク
    "django.contrib.messages",  # メッセージフレームワーク
    "django.contrib.staticfiles",  # 静的ファイルの管理フレームワーク
    "corsheaders",  # CORS対応
    # "rest_framework",  # Django REST Framework
    "trail_status",
    "scheduler",
]

# データベース設定
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# env("DATABASE_URL") を使用
DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=False,
    ),
}
if not DATABASES["default"]:
    raise ValueError("DATABASE_URL 環境変数が設定されていません。")

# ミドルウェア
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS対応（CommonMiddlewareの前に配置）
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# URL設定
ROOT_URLCONF = "config.urls"

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
        },
    },
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstaticの出力先

# WhiteNoise: 静的ファイルの圧縮とキャッシュ最適化
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# プライマリーキーのデフォルトフィールドタイプ
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# WSGIアプリケーションパス設定
WSGI_APPLICATION = "config.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Slack Webhook URL（通知機能用）
# 環境変数 SLACK_WEBHOOK_URL から読み込み
# 設定されていなければ None（通知は送信されない）
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", None)

# ログ設定
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} | {asctime} | {module} | {lineno} | {funcName} | {taskName} | {message}",
            "style": "{",
        },
        "console": {
            "format": "{levelname} | {name} | {lineno} | {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "trail_status": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# https://docs.djangoproject.com/en/6.0/topics/i18n/
LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

# Django REST Framework configuration
"""
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    # 本番ではJSONのみ、開発ではBrowsable APIも有効
    "DEFAULT_RENDERER_CLASSES": (
        ["rest_framework.renderers.JSONRenderer"]
        if IS_PRODUCTION
        else [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ]
    ),
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DATE_FORMAT": "%Y-%m-%d",
}
"""
