"""Instagram · TikTok OAuth — 세션 격리 · 계정 중복 차단."""

from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

from db import _now, connect
from session_utils import platform_user_hash, session_hash

OAUTH_PLATFORMS = frozenset({"instagram", "tiktok"})
SESSION_TTL_HOURS = 24
STATE_TTL_MINUTES = 10


def _public_base_url() -> str:
    return (os.environ.get("CREATIER_PUBLIC_URL") or "http://localhost:8100").rstrip("/")


def oauth_configured(platform: str) -> bool:
    if os.environ.get("CREATIER_OAUTH_DEV", "").lower() in ("1", "true", "yes"):
        return True
    if platform == "instagram":
        return bool(os.environ.get("META_APP_ID") and os.environ.get("META_APP_SECRET"))
    if platform == "tiktok":
        return bool(os.environ.get("TIKTOK_CLIENT_KEY") and os.environ.get("TIKTOK_CLIENT_SECRET"))
    return False


def _redirect_uri(platform: str) -> str:
    return f"{_public_base_url()}/oauth/{platform}/callback"


def start_oauth(platform: str, session_id: str) -> tuple[str | None, str | None]:
    if platform not in OAUTH_PLATFORMS:
        return None, "invalid_platform"
    if not session_id:
        return None, "session_required"
    if not oauth_configured(platform):
        return None, "oauth_not_configured"

    state = secrets.token_urlsafe(32)
    sh = session_hash(session_id)
    exp = (datetime.now(timezone.utc) + timedelta(minutes=STATE_TTL_MINUTES)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    with connect() as conn:
        conn.execute(
            """INSERT INTO oauth_states (state, session_hash, platform, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (state, sh, platform, exp, _now()),
        )

    if os.environ.get("CREATIER_OAUTH_DEV", "").lower() in ("1", "true", "yes"):
        return f"/oauth/{platform}/callback?code=dev&state={urllib.parse.quote(state)}", None

    redirect = urllib.parse.quote(_redirect_uri(platform), safe="")
    if platform == "instagram":
        app_id = os.environ["META_APP_ID"]
        scope = urllib.parse.quote("instagram_basic,pages_show_list")
        url = (
            f"https://www.facebook.com/v21.0/dialog/oauth"
            f"?client_id={app_id}&redirect_uri={redirect}&state={urllib.parse.quote(state)}"
            f"&scope={scope}&response_type=code"
        )
        return url, None

    client_key = os.environ["TIKTOK_CLIENT_KEY"]
    scope = urllib.parse.quote("user.info.basic")
    url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}&scope={scope}&response_type=code"
        f"&redirect_uri={redirect}&state={urllib.parse.quote(state)}"
    )
    return url, None


def _http_post_json(url: str, data: dict, headers: dict | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _exchange_instagram(code: str) -> tuple[str, str, str | None]:
    if code == "dev":
        uid = f"ig-dev-{uuid.uuid4().hex[:8]}"
        return uid, f"ig_user_{uid[-6:]}", None
    app_id = os.environ["META_APP_ID"]
    secret = os.environ["META_APP_SECRET"]
    redirect = urllib.parse.quote(_redirect_uri("instagram"), safe="")
    token_url = (
        f"https://graph.facebook.com/v21.0/oauth/access_token"
        f"?client_id={app_id}&client_secret={secret}&redirect_uri={redirect}&code={urllib.parse.quote(code)}"
    )
    tok = _http_get_json(token_url)
    access = tok.get("access_token")
    if not access:
        return "", "", "token_failed"
    me = _http_get_json(
        f"https://graph.facebook.com/v21.0/me?fields=id,name&access_token={urllib.parse.quote(access)}"
    )
    uid = str(me.get("id") or "")
    name = str(me.get("name") or uid)
    if not uid:
        return "", "", "profile_failed"
    return uid, name, None


def _exchange_tiktok(code: str) -> tuple[str, str, str | None]:
    if code == "dev":
        uid = f"tt-dev-{uuid.uuid4().hex[:8]}"
        return uid, f"tiktok_{uid[-6:]}", None
    client_key = os.environ["TIKTOK_CLIENT_KEY"]
    secret = os.environ["TIKTOK_CLIENT_SECRET"]
    try:
        tok = _http_post_json(
            "https://open.tiktokapis.com/v2/oauth/token/",
            {
                "client_key": client_key,
                "client_secret": secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _redirect_uri("tiktok"),
            },
        )
    except urllib.error.HTTPError:
        return "", "", "token_failed"
    access = (tok.get("data") or tok).get("access_token") or tok.get("access_token")
    if not access:
        return "", "", "token_failed"
    try:
        req = urllib.request.Request(
            "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,username",
            method="GET",
        )
        req.add_header("Authorization", f"Bearer {access}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            info = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return "", "", "profile_failed"
    user = ((info.get("data") or {}).get("user") or {})
    uid = str(user.get("open_id") or "")
    name = str(user.get("display_name") or user.get("username") or uid)
    if not uid:
        return "", "", "profile_failed"
    return uid, name, None


def _bind_platform_session(sh: str, platform: str, uid: str, username: str) -> None:
    puh = platform_user_hash(platform, uid)
    exp = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    with connect() as conn:
        conn.execute("DELETE FROM platform_sessions WHERE platform = ? AND platform_user_hash = ?", (platform, puh))
        conn.execute("DELETE FROM platform_sessions WHERE session_hash = ? AND platform = ?", (sh, platform))
        conn.execute(
            """INSERT INTO platform_sessions
               (session_hash, platform, platform_user_hash, username, connected_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sh, platform, puh, username[:80], _now(), exp),
        )


def complete_oauth(platform: str, code: str, state: str) -> tuple[str | None, str | None]:
    if platform not in OAUTH_PLATFORMS:
        return None, "invalid_platform"
    now = _now()
    with connect() as conn:
        row = conn.execute(
            "SELECT session_hash, expires_at FROM oauth_states WHERE state = ? AND platform = ?",
            (state, platform),
        ).fetchone()
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    if not row:
        return None, "state_invalid"
    if row["expires_at"] <= now:
        return None, "state_expired"

    if platform == "instagram":
        uid, username, err = _exchange_instagram(code)
    else:
        uid, username, err = _exchange_tiktok(code)
    if err:
        return None, err

    _bind_platform_session(row["session_hash"], platform, uid, username)
    return username, None


def get_platform_sessions(session_id: str) -> dict[str, dict]:
    sh = session_hash(session_id)
    now = _now()
    out: dict[str, dict] = {}
    with connect() as conn:
        rows = conn.execute(
            """SELECT platform, username, connected_at, expires_at
               FROM platform_sessions WHERE session_hash = ?""",
            (sh,),
        ).fetchall()
        for r in rows:
            if r["expires_at"] <= now:
                conn.execute(
                    "DELETE FROM platform_sessions WHERE session_hash = ? AND platform = ?",
                    (sh, r["platform"]),
                )
                continue
            out[r["platform"]] = {
                "connected": True,
                "username": r["username"],
                "connectedAt": r["connected_at"],
            }
    return out


def require_platform_auth(session_id: str, platform: str) -> tuple[bool, str | None]:
    if platform not in OAUTH_PLATFORMS:
        return True, None
    sessions = get_platform_sessions(session_id)
    if platform in sessions:
        return True, None
    if oauth_configured(platform):
        return False, f"{platform}_auth_required"
    if os.environ.get("CREATIER_OAUTH_DEV", "").lower() in ("1", "true", "yes"):
        return False, f"{platform}_auth_required"
    return False, "oauth_not_configured"


def disconnect_platform(session_id: str, platform: str) -> None:
    sh = session_hash(session_id)
    with connect() as conn:
        conn.execute(
            "DELETE FROM platform_sessions WHERE session_hash = ? AND platform = ?",
            (sh, platform),
        )


def oauth_status(session_id: str) -> dict:
    sessions = get_platform_sessions(session_id)
    return {
        "instagram": {
            "configured": oauth_configured("instagram"),
            "connected": "instagram" in sessions,
            **(sessions.get("instagram") or {}),
        },
        "tiktok": {
            "configured": oauth_configured("tiktok"),
            "connected": "tiktok" in sessions,
            **(sessions.get("tiktok") or {}),
        },
    }
