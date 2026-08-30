import os

import requests
from dotenv import load_dotenv

load_dotenv(".env.local")


def send_simple_message():
    res = requests.post(
        "https://api.mailgun.net/v3/trail-info.jp/messages",
        auth=("api", os.getenv("MAILGUN_API_KEY", "API_KEY")),
        data={
            "from": os.getenv("EMAIL_SENDER_NOREPLY"),
            "to": os.getenv("EMAIL_RECIPIENTS", "").split(","),
            "subject": "Hello from Trail Info",
            "text": "Congratulations Trail Info, you just sent an email with Mailgun! You are truly awesome!",
        },
    )

    print(res.status_code)


send_simple_message()
