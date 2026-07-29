"""악용 신고 접수 — 계산 데이터와 분리 저장."""

from __future__ import annotations

import uuid

from db import _now, connect

REPORT_CATEGORIES = {
    "ads": "광고·협찬 문의",
    "collaboration": "제휴·협업 문의",
    "inquiry": "문의·제안",
    "impersonation": "타인 활동명·채널명 도용",
    "false_info": "허위 수익·세금 정보 유포",
    "spam": "반복·자동 계산 등 서비스 남용",
    "reserved_name": "보호 활동명 무단 사용 시도",
    "other": "기타",
}

NOTIFY_CATEGORIES = frozenset({"ads", "collaboration", "inquiry"})


def submit_report(category: str, detail: str, contact: str = "") -> tuple[dict | None, str | None]:
    cat = (category or "").strip()
    if cat not in REPORT_CATEGORIES:
        return None, "invalid_category"
    body = (detail or "").strip()
    if len(body) < 10:
        return None, "detail_too_short"
    if len(body) > 2000:
        return None, "detail_too_long"
    contact_clean = (contact or "").strip()[:120]

    rid = f"rpt-{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """INSERT INTO abuse_reports (id, category, detail, contact, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (rid, cat, body, contact_clean or None, _now()),
        )
    result = {"id": rid, "status": "pending", "category": cat, "categoryLabel": REPORT_CATEGORIES[cat], "detail": body, "contact": contact_clean}
    if cat in NOTIFY_CATEGORIES:
        try:
            from notify import notify_report_received

            notify_report_received(result)
        except Exception:
            pass
    return result, None


def list_reports(limit: int = 100) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT id, category, detail, contact, status, created_at
               FROM abuse_reports ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "category": r["category"],
            "categoryLabel": REPORT_CATEGORIES.get(r["category"], r["category"]),
            "detail": r["detail"],
            "contact": r["contact"],
            "status": r["status"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]
