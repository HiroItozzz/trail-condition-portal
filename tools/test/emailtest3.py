"""send_mail()のテスト
---  Django settingsで必要な変数 ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.mailgun.org"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_SENDER_NOREPLY")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_PASSWORD_NOREPLY")
"""

import os
import sys
from pathlib import Path

import django
from dotenv import load_dotenv

load_dotenv(".env.local")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()

from django.conf import settings
from django.core.mail import send_mail


def main():
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails: list[str] = getattr(settings, "NOTIFICATION_RECIPIENTS", [])

    res = send_mail(
        subject="ジャンゴのメールテスト",
        message="本文です",
        from_email=from_email,
        recipient_list=to_emails,
        fail_silently=False,
    )
    print(res)


if __name__ == "__main__":
    main()
