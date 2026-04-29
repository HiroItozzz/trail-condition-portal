from .base import *

if DEBUG:
    raise ValueError("本番環境で DEBUG=True は許可されていません")

if not SECRET_KEY or "insecure" in SECRET_KEY:
    raise ValueError("本番環境用のSECRET_KEYを設定してください")

# ======================================================

ALLOWED_HOSTS = ["trail-info.jp", "www.trail-info.jp"]
ALLOWED_HOSTS += [h for h in os.environ.get("EXTRA_ALLOWED_HOSTS", "").split(",") if h]

# この設定により、Cloudflare が付与する X-Forwarded-Proto: https ヘッダーを見て「実際は HTTPS だ」と判断できます。
# これがないと: request.is_secure() が常に False / CSRF 検証が失敗する可能性 / リダイレクトURLが http:// になる
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    "https://trail-info.jp",
    "https://www.trail-info.jp",
]
CORS_ALLOWED_ORIGINS = [
    "https://trail-info.jp",
    "https://www.trail-info.jp",
]

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
