"""브라우저 세션 해시 — OAuth·calc·share 격리."""

from __future__ import annotations

import hashlib
import os


def session_hash(session_id: str) -> str:
    sid = (session_id or "anon")[:64]
    salt = os.environ.get("AUTH_SECRET", "creatier-local-dev-secret-32chars-minimum")
    return hashlib.sha256(f"sid|{sid}|{salt}".encode("utf-8")).hexdigest()


def platform_user_hash(platform: str, platform_user_id: str) -> str:
    salt = os.environ.get("AUTH_SECRET", "creatier-local-dev-secret-32chars-minimum")
    raw = f"{platform}|{platform_user_id}|{salt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
