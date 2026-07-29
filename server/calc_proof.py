"""계산 증명 — 1회용 · 세션 바인딩 · 공유 후 즉시 파기."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from db import _now, connect
from session_utils import session_hash

PROOF_TTL_MINUTES = 15


def _items_fingerprint(items: list[dict], creator_name: str) -> str:
    norm = []
    for it in sorted(items, key=lambda x: x.get("platformId") or ""):
        norm.append(
            {
                "platformId": (it.get("platformId") or "").strip(),
                "gross": int(round(float(it.get("gross") or 0))),
            }
        )
    payload = {"creatorName": (creator_name or "").strip(), "items": norm}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_calc_proof(session_id: str, items: list[dict], creator_name: str) -> str:
    sh = session_hash(session_id)
    fp = _items_fingerprint(items, creator_name)
    proof = secrets.token_urlsafe(24)
    proof_h = hashlib.sha256(proof.encode("utf-8")).hexdigest()
    exp = (datetime.now(timezone.utc) + timedelta(minutes=PROOF_TTL_MINUTES)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    pid = f"prf-{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """INSERT INTO calc_proofs
               (id, proof_hash, session_hash, payload_fingerprint, expires_at, used, created_at)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (pid, proof_h, sh, fp, exp, _now()),
        )
    return proof


def consume_calc_proof(
    session_id: str,
    proof: str,
    items: list[dict],
    creator_name: str,
) -> tuple[bool, str | None]:
    if not proof or len(proof) < 16:
        return False, "proof_required"
    sh = session_hash(session_id)
    proof_h = hashlib.sha256(proof.encode("utf-8")).hexdigest()
    fp = _items_fingerprint(items, creator_name)
    now = _now()
    with connect() as conn:
        row = conn.execute(
            """SELECT id, session_hash, payload_fingerprint, expires_at, used
               FROM calc_proofs WHERE proof_hash = ?""",
            (proof_h,),
        ).fetchone()
        if not row:
            return False, "proof_invalid"
        if row["used"]:
            return False, "proof_used"
        if row["expires_at"] <= now:
            conn.execute("DELETE FROM calc_proofs WHERE id = ?", (row["id"],))
            return False, "proof_expired"
        if row["session_hash"] != sh:
            return False, "session_mismatch"
        if row["payload_fingerprint"] != fp:
            return False, "payload_mismatch"
        conn.execute("DELETE FROM calc_proofs WHERE id = ?", (row["id"],))
    return True, None
