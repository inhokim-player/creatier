"""HTTP 보안 헤더 · 로그인 시도 제한."""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone

from db import connect, _now

AUTH_COOKIE = "creatier_admin"
LOGIN_WINDOW_SEC = 900
LOGIN_MAX_ATTEMPTS = 5

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "font-src https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}


def apply_security_headers(response, path: str = ""):
    for key, value in _SECURITY_HEADERS.items():
        response.headers[key] = value
    if path.startswith("/admin") or path.startswith("/login") or path.startswith("/api/auth"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    if path.startswith("/verify") or path.startswith("/api/share"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _ip_hash(ip: str) -> str:
    salt = os.environ.get("AUTH_SECRET", "creatier-local-dev-secret-32chars-minimum")
    raw = f"{ip}|{salt}".encode()
    return hashlib.sha256(raw).hexdigest()


def _client_ip(request) -> str:
    if not request:
        return "unknown"
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or (request.remote_addr or "unknown")


def login_allowed(request) -> tuple[bool, str | None]:
    ip = _client_ip(request)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=LOGIN_WINDOW_SEC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ip_h = _ip_hash(ip)
    with connect() as conn:
        conn.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,))
        count = conn.execute(
            "SELECT COUNT(*) c FROM login_attempts WHERE ip_hash = ? AND attempted_at >= ?",
            (ip_h, cutoff),
        ).fetchone()["c"]
    if count >= LOGIN_MAX_ATTEMPTS:
        return False, "too_many_attempts"
    return True, None


def record_login_failure(request) -> None:
    ip_h = _ip_hash(_client_ip(request))
    with connect() as conn:
        conn.execute(
            "INSERT INTO login_attempts (ip_hash, attempted_at) VALUES (?, ?)",
            (ip_h, _now()),
        )


def clear_login_failures(request) -> None:
    ip_h = _ip_hash(_client_ip(request))
    with connect() as conn:
        conn.execute("DELETE FROM login_attempts WHERE ip_hash = ?", (ip_h,))


def client_ip_hash(request) -> str:
    return _ip_hash(_client_ip(request))


def safe_redirect_path(raw: str | None) -> str:
    """오픈 리다이렉트 방지 — 같은 사이트 내부 경로만."""
    if not raw:
        return "/admin"
    path = str(raw).strip()
    if not path.startswith("/") or path.startswith("//"):
        return "/admin"
    if "://" in path or "\\" in path:
        return "/admin"
    if not re.match(r"^/[A-Za-z0-9_./?=&%-]*$", path):
        return "/admin"
    if path.startswith("/login"):
        return "/admin"
    return path
