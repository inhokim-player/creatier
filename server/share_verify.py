"""Instagram · TikTok 수익 인증 공유 — 토큰 링크 · 만료 · 조회 제한."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

from abuse_guard import is_reserved_name, normalize_creator_name
from calc_proof import consume_calc_proof
from db import _now, connect
from platform_oauth import get_platform_sessions, require_platform_auth
from platforms import net_after_fee, platform_by_id
from session_utils import session_hash

SHARE_PLATFORMS = frozenset({"instagram", "tiktok"})
SHARE_TTL_DAYS = 7
MAX_VIEWS = 100
MAX_SHARES_PER_DAY = 5
PIN_PATTERN = re.compile(r"^\d{4}$")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def _expires_at() -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=SHARE_TTL_DAYS)
    return exp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _period_label() -> str:
    today = date.today()
    return f"{today.year}년 {today.month}월"


def _ip_share_count(ip_hash: str) -> int:
    day = date.today().isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT share_count FROM share_daily WHERE day = ? AND ip_hash = ?",
            (day, ip_hash),
        ).fetchone()
    return int(row["share_count"]) if row else 0


def _record_share(ip_hash: str) -> None:
    day = date.today().isoformat()
    with connect() as conn:
        conn.execute(
            """INSERT INTO share_daily (day, ip_hash, share_count)
               VALUES (?, ?, 1)
               ON CONFLICT(day, ip_hash) DO UPDATE SET share_count = share_count + 1""",
            (day, ip_hash),
        )


def _build_platform_rows(items: list[dict]) -> tuple[list[dict], dict]:
    rows = []
    total_gross = total_fee = total_wh = total_net = 0
    for it in items:
        pid = (it.get("platformId") or "").strip()
        gross = float(it.get("gross") or 0)
        if pid not in SHARE_PLATFORMS or gross <= 0:
            continue
        calc = net_after_fee(gross, pid)
        spec = platform_by_id(pid)
        rows.append(
            {
                "platformId": pid,
                "platform": spec.name if spec else pid,
                "gross": calc["gross"],
                "platformFee": calc["platformFee"],
                "withholding": calc["withholding"],
                "withholdingLabel": calc["withholdingLabel"],
                "net": calc["net"],
            }
        )
        total_gross += calc["gross"]
        total_fee += calc["platformFee"]
        total_wh += calc["withholding"]
        total_net += calc["net"]
    totals = {
        "gross": round(total_gross),
        "platformFee": round(total_fee),
        "withholding": round(total_wh),
        "net": round(total_net),
    }
    return rows, totals


def create_revenue_share(
    creator_name: str,
    items: list[dict],
    *,
    session_id: str = "",
    calc_proof: str = "",
    pin: str | None = None,
    ip_hash: str = "",
) -> tuple[dict | None, str | None]:
    if not session_id:
        return None, "session_required"
    ok, err = consume_calc_proof(session_id, calc_proof, items, creator_name)
    if not ok:
        return None, err or "proof_invalid"

    display = (creator_name or "").strip()
    if len(display) < 2:
        return None, "name_required"
    if len(display) > 40:
        return None, "name_too_long"
    if is_reserved_name(display):
        return None, "name_reserved"

    if ip_hash and _ip_share_count(ip_hash) >= MAX_SHARES_PER_DAY:
        return None, "share_limit_reached"

    rows, totals = _build_platform_rows(items)
    if not rows:
        return None, "no_share_platform"

    platform_auth = get_platform_sessions(session_id)
    verified_platforms = {}
    for row in rows:
        pid = row["platformId"]
        auth_ok, auth_err = require_platform_auth(session_id, pid)
        if not auth_ok:
            return None, auth_err
        info = platform_auth.get(pid) or {}
        verified_platforms[pid] = info.get("username") or ""
        row["verifiedAccount"] = info.get("username") or ""

    sh = session_hash(session_id)
    pin_clean = (pin or "").strip()
    pin_hash = None
    if pin_clean:
        if not PIN_PATTERN.match(pin_clean):
            return None, "pin_invalid"
        from werkzeug.security import generate_password_hash

        pin_hash = generate_password_hash(pin_clean, method="scrypt")

    token = secrets.token_urlsafe(32)
    sid = f"shr-{uuid.uuid4().hex[:12]}"
    payload = {
        "creatorName": display,
        "period": _period_label(),
        "platforms": rows,
        "totals": totals,
        "verifiedPlatforms": verified_platforms,
        "verifiedAt": _now(),
    }

    with connect() as conn:
        conn.execute(
            """INSERT INTO revenue_shares
               (id, token_hash, session_hash, creator_name, payload_json, pin_hash, expires_at,
                view_count, max_views, revoked, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 0, ?)""",
            (
                sid,
                _hash_token(token),
                sh,
                display,
                json.dumps(payload, ensure_ascii=False),
                pin_hash,
                _expires_at(),
                MAX_VIEWS,
                _now(),
            ),
        )

    if ip_hash:
        _record_share(ip_hash)

    return {
        "id": sid,
        "token": token,
        "expiresInDays": SHARE_TTL_DAYS,
        "pinRequired": bool(pin_hash),
        "platformCount": len(rows),
    }, None


def get_revenue_share(token: str, pin: str | None = None) -> tuple[dict | None, str | None]:
    raw = (token or "").strip()
    if len(raw) < 16:
        return None, "invalid_token"

    th = _hash_token(raw)
    now = _now()
    with connect() as conn:
        row = conn.execute(
            """SELECT id, creator_name, payload_json, pin_hash, expires_at,
                      view_count, max_views, revoked
               FROM revenue_shares WHERE token_hash = ?""",
            (th,),
        ).fetchone()
        if not row:
            return None, "not_found"
        if row["revoked"]:
            return None, "revoked"
        if row["expires_at"] <= now:
            return None, "expired"
        if row["view_count"] >= row["max_views"]:
            return None, "view_limit"

        if row["pin_hash"]:
            pin_clean = (pin or "").strip()
            if not pin_clean:
                return None, "pin_required"
            from werkzeug.security import check_password_hash

            if not check_password_hash(row["pin_hash"], pin_clean):
                return None, "pin_wrong"

        conn.execute(
            "UPDATE revenue_shares SET view_count = view_count + 1 WHERE id = ?",
            (row["id"],),
        )

    payload = json.loads(row["payload_json"])
    return {
        "ok": True,
        "creatorName": payload.get("creatorName") or row["creator_name"],
        "period": payload.get("period"),
        "platforms": payload.get("platforms") or [],
        "totals": payload.get("totals") or {},
        "verifiedAt": payload.get("verifiedAt"),
    }, None
