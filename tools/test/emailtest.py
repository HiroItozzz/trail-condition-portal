import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv(".env.local")

msg = MIMEMultipart()
msg["From"] = os.environ.get("EMAIL_SENDER_NOREPLY")
msg["To"] = "contact@trail-info.jp"
msg["Subject"] = "テスト"
msg.attach(MIMEText("こんにちは", "plain", "utf-8"))

with smtplib.SMTP("smtp.mailgun.org", 587) as server:
    server.starttls()
    server.login(os.environ.get("EMAIL_SENDER_NOREPLY"), os.environ.get("EMAIL_PASSWORD_NOREPLY"))
    server.send_message(msg)
