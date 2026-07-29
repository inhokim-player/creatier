"""익명 사용 통계 · 활동명 중복 악용 방지 · 누적 금액 집계(개인 식별 없음)."""

from __future__ import annotations

import hashlib
from datetime import date

from abuse_guard import is_reserved_name, normalize_creator_name
from db import connect, _now

MAX_NAME_CALCS_PER_DAY = 3


def _name_hash(name: str) -> str:
    norm = normalize_creator_name(name)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def name_usage_today(creator_name: str) -> int:
    day = date.today().isoformat()
    nh = _name_hash((creator_name or "").strip())
    with connect() as conn:
        row = conn.execute(
            "SELECT calc_count FROM usage_name_daily WHERE day = ? AND name_hash = ?",
            (day, nh),
        ).fetchone()
    return int(row["calc_count"]) if row else 0


def validate_calc_session(session_id: str, creator_name: str) -> tuple[bool, str | None]:
    display = (creator_name or "").strip()
    if len(display) < 2:
        return False, "name_required"
    if len(display) > 40:
        return False, "name_too_long"
    if is_reserved_name(display):
        return False, "name_reserved"

    day = date.today().isoformat()
    sid = (session_id or "anon")[:64]
    nh = _name_hash(display)

    with connect() as conn:
        if conn.execute(
            "SELECT 1 FROM usage_session_calc WHERE day = ? AND session_hash = ?",
            (day, sid),
        ).fetchone():
            return False, "session_used"

        row = conn.execute(
            "SELECT calc_count FROM usage_name_daily WHERE day = ? AND name_hash = ?",
            (day, nh),
        ).fetchone()
        used = int(row["calc_count"]) if row else 0
        if used >= MAX_NAME_CALCS_PER_DAY:
            return False, "name_limit_reached"

    return True, None


def record_calculation(
    session_id: str,
    creator_name: str,
    *,
    gross: float = 0,
    net: float = 0,
    payable: float = 0,
) -> None:
    day = date.today().isoformat()
    sid = (session_id or "anon")[:64]
    nh = _name_hash((creator_name or "").strip())
    g, n, p = float(gross or 0), float(net or 0), float(payable or 0)

    with connect() as conn:
        conn.execute(
            """INSERT INTO usage_daily (day, calc_count, gross_sum, net_sum, payable_sum)
               VALUES (?, 1, ?, ?, ?)
               ON CONFLICT(day) DO UPDATE SET
                 calc_count = calc_count + 1,
                 gross_sum = gross_sum + excluded.gross_sum,
                 net_sum = net_sum + excluded.net_sum,
                 payable_sum = payable_sum + excluded.payable_sum""",
            (day, g, n, p),
        )
        conn.execute(
            """UPDATE usage_aggregate SET
                 total_gross = total_gross + ?,
                 total_net = total_net + ?,
                 total_payable = total_payable + ?
               WHERE id = 1""",
            (g, n, p),
        )
        conn.execute(
            """INSERT OR IGNORE INTO usage_sessions (day, session_hash, created_at)
               VALUES (?, ?, ?)""",
            (day, sid, _now()),
        )
        conn.execute(
            """INSERT OR IGNORE INTO usage_session_calc (day, session_hash, created_at)
               VALUES (?, ?, ?)""",
            (day, sid, _now()),
        )
        conn.execute(
            """INSERT INTO usage_name_daily (day, name_hash, calc_count, created_at)
               VALUES (?, ?, 1, ?)
               ON CONFLICT(day, name_hash) DO UPDATE SET calc_count = calc_count + 1""",
            (day, nh, _now()),
        )


def admin_usage_stats() -> dict:
    day = date.today().isoformat()
    with connect() as conn:
        today_row = conn.execute(
            "SELECT calc_count, gross_sum, net_sum, payable_sum FROM usage_daily WHERE day = ?",
            (day,),
        ).fetchone()
        agg = conn.execute(
            "SELECT total_gross, total_net, total_payable FROM usage_aggregate WHERE id = 1"
        ).fetchone()
        total_calcs = conn.execute("SELECT COALESCE(SUM(calc_count), 0) c FROM usage_daily").fetchone()["c"]
        total_users = conn.execute("SELECT COUNT(*) c FROM usage_sessions").fetchone()["c"]
        today_users = conn.execute(
            "SELECT COUNT(*) c FROM usage_sessions WHERE day = ?", (day,)
        ).fetchone()["c"]
        pending_reports = conn.execute(
            "SELECT COUNT(*) c FROM abuse_reports WHERE status = 'pending'"
        ).fetchone()["c"]
        total_reports = conn.execute("SELECT COUNT(*) c FROM abuse_reports").fetchone()["c"]
    return {
        "totalUsers": total_users,
        "todayUsers": today_users,
        "totalCalculations": total_calcs,
        "todayCalculations": today_row["calc_count"] if today_row else 0,
        "totalGross": agg["total_gross"] if agg else 0,
        "totalNet": agg["total_net"] if agg else 0,
        "totalPayable": agg["total_payable"] if agg else 0,
        "todayGross": today_row["gross_sum"] if today_row else 0,
        "todayNet": today_row["net_sum"] if today_row else 0,
        "pendingReports": pending_reports,
        "totalReports": total_reports,
        "dailyNameLimit": MAX_NAME_CALCS_PER_DAY,
    }
