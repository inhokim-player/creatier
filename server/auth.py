"""Creatier 인증 — 관리자 전용 · HttpOnly 쿠키 · DB 재검증."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from werkzeug.security import check_password_hash

from db import find_user_by_email, find_user_by_id
from http_security import AUTH_COOKIE, clear_login_failures, login_allowed, record_login_failure

TOKEN_TTL_SEC = 7 * 24 * 3600
DEMO_SECRET = "creatier-local-dev-secret-32chars-minimum"


def _secret() -> str:
    return os.environ.get("AUTH_SECRET", DEMO_SECRET)


def _cookie_secure(request) -> bool:
    from security import is_production

    if is_production():
        return True
    return bool(getattr(request, "is_secure", False))


def verify_password(user: dict, password: str) -> bool:
    stored = user.get("password", "")
    if not stored:
        return False
    if str(stored).startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, password or "")
    return False


def create_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user.get("role", "platform"),
        "exp": int(time.time()) + TOKEN_TTL_SEC,
        "v": 2,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
    data = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(_secret().encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"


def decode_token(token: str):
    if not token or "." not in token:
        return None
    data, sig = token.rsplit(".", 1)
    expected = hmac.new(_secret().encode(), data.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    pad = "=" * (-len(data) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(data + pad))
    except (json.JSONDecodeError, ValueError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def _user_from_payload(payload: dict | None):
    if not payload:
        return None
    user = find_user_by_id(payload.get("sub"))
    if not user or user.get("status") != "active" or user.get("role") != "platform":
        return None
    if user.get("email", "").lower() != (payload.get("email") or "").lower():
        return None
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user.get("role"),
    }


def extract_token(auth_header: str | None, cookie_token: str | None) -> str | None:
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return auth_header.strip()
    if cookie_token:
        return cookie_token.strip()
    return None


def get_current_user(auth_header: str | None = None, cookie_token: str | None = None):
    token = extract_token(auth_header, cookie_token)
    if not token:
        return None
    return _user_from_payload(decode_token(token))


def attach_auth_cookie(response, token: str, request):
    response.set_cookie(
        AUTH_COOKIE,
        token,
        httponly=True,
        samesite="Lax",
        secure=_cookie_secure(request),
        max_age=TOKEN_TTL_SEC,
        path="/",
    )
    return response


def clear_auth_cookie(response):
    response.delete_cookie(AUTH_COOKIE, path="/")
    return response


def login(email: str, password: str, request=None):
    if request is not None:
        allowed, err = login_allowed(request)
        if not allowed:
            return None, err or "too_many_attempts"

    user = find_user_by_email(email)
    if not user or not verify_password(user, password):
        if request is not None:
            record_login_failure(request)
        return None, "invalid_credentials"
    if user.get("status") != "active" or user.get("role") != "platform":
        if request is not None:
            record_login_failure(request)
        return None, "invalid_credentials"

    if request is not None:
        clear_login_failures(request)

    token = create_token(user)
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name", ""),
            "role": user.get("role"),
        },
        "expiresIn": TOKEN_TTL_SEC,
    }, None
