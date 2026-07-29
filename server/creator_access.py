"""활동명 PIN · 접근 토큰 (세션별, 악용 방지)."""

from __future__ import annotations

import hashlib
import secrets

from abuse_guard import is_reserved_name, normalize_creator_name, pin_valid
from db import connect, _now
from werkzeug.security import check_password_hash, generate_password_hash


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def creator_status(name: str) -> dict:
    norm = normalize_creator_name(name)
    if not norm:
        return {"ok": False, "error": "name_required"}
    reserved = is_reserved_name(name)
    row = _get_access(norm)
    return {
        "ok": True,
        "name": name.strip(),
        "nameNorm": norm,
        "reserved": reserved,
        "claimed": row is not None,
        "canSave": not reserved,
        "needsPin": not reserved and row is not None,
    }


def claim_creator(name: str, pin: str) -> tuple[dict | None, str | None]:
    display = name.strip()
    norm = normalize_creator_name(display)
    if not norm:
        return None, "name_required"
    if is_reserved_name(display):
        return None, "reserved_name"
    if not pin_valid(pin):
        return None, "pin_invalid"
    if _get_access(norm):
        return None, "already_claimed"

    token = secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute(
            """INSERT INTO creator_access (name_norm, display_name, pin_hash, token_hash, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (norm, display, generate_password_hash(pin, method="scrypt"), _hash_token(token), _now()),
        )
    return {"accessToken": token, "displayName": display, "claimed": True}, None


def unlock_creator(name: str, pin: str) -> tuple[dict | None, str | None]:
    display = name.strip()
    norm = normalize_creator_name(display)
    if not norm:
        return None, "name_required"
    if is_reserved_name(display):
        return None, "reserved_name"
    if not pin_valid(pin):
        return None, "pin_invalid"

    row = _get_access(norm)
    if not row:
        return None, "not_claimed"
    if not check_password_hash(row["pin_hash"], pin):
        return None, "pin_wrong"

    token = secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute(
            "UPDATE creator_access SET token_hash = ?, display_name = ? WHERE name_norm = ?",
            (_hash_token(token), display, norm),
        )
    return {"accessToken": token, "displayName": row["display_name"]}, None


def verify_access(name: str, token: str) -> tuple[bool, str | None, str | None]:
    """Returns (ok, display_name, error_code)."""
    display = name.strip()
    norm = normalize_creator_name(display)
    if not norm:
        return False, None, "name_required"
    if is_reserved_name(display):
        return False, None, "reserved_name"
    if not token:
        return False, None, "auth_required"

    row = _get_access(norm)
    if not row:
        return False, None, "not_claimed"
    if row["token_hash"] != _hash_token(token.strip()):
        return False, None, "invalid_token"
    return True, row["display_name"], None


def require_write_access(name: str, token: str) -> tuple[str | None, str | None]:
    display = name.strip()
    if is_reserved_name(display):
        return None, "reserved_name"
    ok, display, err = verify_access(name, token)
    if not ok:
        return None, err
    return display, None


def _get_access(name_norm: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT name_norm, display_name, pin_hash, token_hash FROM creator_access WHERE name_norm = ?",
            (name_norm,),
        ).fetchone()
    return dict(row) if row else None
