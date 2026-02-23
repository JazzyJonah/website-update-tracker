import os
import sys
import re
import smtplib
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup

URL = os.environ["TARGET_URL"]
CSS_SELECTOR = os.environ["CSS_SELECTOR"]

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]

STATE_FILE = "last_value.txt"


def extract_value(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one(CSS_SELECTOR)
    if el is None:
        raise RuntimeError(f"Could not find element for selector: {CSS_SELECTOR}")
    # Normalize whitespace
    value = re.sub(r"\s+", " ", el.get_text(strip=True)).strip()
    return value


def read_previous() -> str | None:
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None


def write_current(value: str) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(value)


def send_email(subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


def main() -> int:
    r = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (GitHub Actions monitor)"},
        timeout=30,
    )
    r.raise_for_status()

    current = extract_value(r.text)
    previous = read_previous()

    print(f"Previous: {previous}")
    print(f"Current : {current}")

    if previous is None:
        write_current(current)
        print("Initialized state; no email sent.")
        return 0

    if current != previous:
        write_current(current)
        subject = f"Website updated: {URL}"
        body = (
            f"Change detected for selector: {CSS_SELECTOR}\n\n"
            f"URL: {URL}\n\n"
            f"Previous:\n{previous}\n\n"
            f"Current:\n{current}\n"
        )
        send_email(subject, body)
        print("Change detected; email sent.")
    else:
        print("No change detected; no email sent.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
