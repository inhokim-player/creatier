"""관리자 이메일 알림 — Resend / SMTP / 로컬 로그."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIL_LOG = ROOT / "data" / "mail-log.json"

DEFAULT_CONTACT_EMAIL = "a123dlsgh@gmail.com"


def contact_email() -> str:
    return (
        os.environ.get("CREATIER_CONTACT_EMAIL")
        or os.environ.get("CREATIER_ADMIN_EMAIL")
        or DEFAULT_CONTACT_EMAIL
    ).strip().lower()


def admin_email() -> str:
    return contact_email()


def _public_url() -> str:
    return (os.environ.get("CREATIER_PUBLIC_URL") or "http://localhost:8100").rstrip("/")


def _append_log(entry: dict) -> None:
    MAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
    items: list = []
    if MAIL_LOG.is_file():
        try:
            raw = json.loads(MAIL_LOG.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                items = raw
        except Exception:
            items = []
    items.insert(0, entry)
    MAIL_LOG.write_text(json.dumps(items[:200], ensure_ascii=False, indent=2), encoding="utf-8")


def _send_resend(to_addr: str, subject: str, body: str) -> bool:
    api_key = os.environ.get("CREATIER_RESEND_API_KEY", "").strip()
    if not api_key:
        return False
    from_addr = os.environ.get("CREATIER_MAIL_FROM", f"Creatier <onboarding@resend.dev>").strip()
    payload = json.dumps(
        {"from": from_addr, "to": [to_addr], "subject": subject, "text": body},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def _send_smtp(to_addr: str, subject: str, body: str) -> bool:
    host = os.environ.get("CREATIER_SMTP_HOST", "").strip()
    if not host:
        return False
    port = int(os.environ.get("CREATIER_SMTP_PORT", "587"))
    user = os.environ.get("CREATIER_SMTP_USER", "").strip()
    password = os.environ.get("CREATIER_SMTP_PASS", "").strip()
    from_addr = os.environ.get("CREATIER_MAIL_FROM", user or contact_email()).strip()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls(context=ctx)
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        return True
    except Exception:
        return False


def send_admin_email(subject: str, body: str) -> dict:
    to_addr = admin_email()
    sent = _send_resend(to_addr, subject, body) or _send_smtp(to_addr, subject, body)
    entry = {
        "to": to_addr,
        "subject": subject,
        "body": body[:4000],
        "sent": sent,
        "delivery": "email" if sent else "mail_log",
    }
    if not sent:
        _append_log(entry)
    return entry


def notify_report_received(report: dict) -> dict:
    """문의·광고·협업 접수 시 관리자 이메일."""
    cat = report.get("categoryLabel") or report.get("category") or "문의"
    detail = (report.get("detail") or "").strip()
    contact = (report.get("contact") or "").strip() or "(없음)"
    rid = report.get("id") or ""
    admin_url = f"{_public_url()}/admin"
    subject = f"[크라잇에이터] {cat} — {rid}"
    body = (
        f"유형: {cat}\n"
        f"접수 ID: {rid}\n"
        f"연락처: {contact}\n\n"
        f"내용:\n{detail}\n\n"
        f"관리자: {admin_url}\n"
    )
    result = send_admin_email(subject, body)
    result["reportId"] = rid
    return result
