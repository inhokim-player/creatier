"""Creatier SQLite — 수익 입력 · 정산 확인 · 관리자."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_DB = DATA_DIR / "creatier.db"


def db_path() -> str:
    return os.environ.get("CREATIER_DATABASE", str(DEFAULT_DB))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def connect():
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT,
                role TEXT NOT NULL DEFAULT 'platform',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS ledger_entries (
                id TEXT PRIMARY KEY,
                creator_name TEXT NOT NULL,
                platform_id TEXT NOT NULL,
                gross REAL NOT NULL,
                platform_fee REAL NOT NULL,
                withholding REAL NOT NULL,
                net REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                earned_date TEXT NOT NULL,
                expected_deposit_date TEXT,
                confirmed_at TEXT,
                created_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_ledger_name ON ledger_entries(creator_name);
            CREATE INDEX IF NOT EXISTS idx_ledger_status ON ledger_entries(status);

            CREATE TABLE IF NOT EXISTS creator_access (
                name_norm TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS usage_daily (
                day TEXT PRIMARY KEY,
                calc_count INTEGER NOT NULL DEFAULT 0,
                gross_sum REAL NOT NULL DEFAULT 0,
                net_sum REAL NOT NULL DEFAULT 0,
                payable_sum REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS usage_aggregate (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_gross REAL NOT NULL DEFAULT 0,
                total_net REAL NOT NULL DEFAULT 0,
                total_payable REAL NOT NULL DEFAULT 0
            );

            INSERT OR IGNORE INTO usage_aggregate (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS usage_sessions (
                day TEXT NOT NULL,
                session_hash TEXT NOT NULL,
                created_at TEXT,
                PRIMARY KEY (day, session_hash)
            );

            CREATE TABLE IF NOT EXISTS usage_name_daily (
                day TEXT NOT NULL,
                name_hash TEXT NOT NULL,
                calc_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                PRIMARY KEY (day, name_hash)
            );

            CREATE TABLE IF NOT EXISTS usage_session_calc (
                day TEXT NOT NULL,
                session_hash TEXT NOT NULL,
                created_at TEXT,
                PRIMARY KEY (day, session_hash)
            );

            CREATE TABLE IF NOT EXISTS abuse_reports (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                detail TEXT NOT NULL,
                contact TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_hash TEXT NOT NULL,
                attempted_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip_hash, attempted_at);

            CREATE TABLE IF NOT EXISTS revenue_shares (
                id TEXT PRIMARY KEY,
                token_hash TEXT UNIQUE NOT NULL,
                session_hash TEXT,
                creator_name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                pin_hash TEXT,
                expires_at TEXT NOT NULL,
                view_count INTEGER NOT NULL DEFAULT 0,
                max_views INTEGER NOT NULL DEFAULT 100,
                revoked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_revenue_shares_token ON revenue_shares(token_hash);
            CREATE INDEX IF NOT EXISTS idx_revenue_shares_expires ON revenue_shares(expires_at);

            CREATE TABLE IF NOT EXISTS share_daily (
                day TEXT NOT NULL,
                ip_hash TEXT NOT NULL,
                share_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (day, ip_hash)
            );

            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                session_hash TEXT NOT NULL,
                platform TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS platform_sessions (
                session_hash TEXT NOT NULL,
                platform TEXT NOT NULL,
                platform_user_hash TEXT NOT NULL,
                username TEXT NOT NULL,
                connected_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY (session_hash, platform)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_user_unique
                ON platform_sessions(platform, platform_user_hash);

            CREATE TABLE IF NOT EXISTS calc_proofs (
                id TEXT PRIMARY KEY,
                proof_hash TEXT UNIQUE NOT NULL,
                session_hash TEXT NOT NULL,
                payload_fingerprint TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        _migrate_schema(conn)
        _sync_platform_admin(conn)


def _migrate_schema(conn) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(usage_name_daily)").fetchall()}
    if "calc_count" not in cols:
        conn.execute(
            "ALTER TABLE usage_name_daily ADD COLUMN calc_count INTEGER NOT NULL DEFAULT 0"
        )
        conn.execute(
            "UPDATE usage_name_daily SET calc_count = 1 WHERE calc_count = 0"
        )
    daily_cols = {r[1] for r in conn.execute("PRAGMA table_info(usage_daily)").fetchall()}
    for col, typ in (
        ("gross_sum", "REAL NOT NULL DEFAULT 0"),
        ("net_sum", "REAL NOT NULL DEFAULT 0"),
        ("payable_sum", "REAL NOT NULL DEFAULT 0"),
    ):
        if col not in daily_cols:
            conn.execute(f"ALTER TABLE usage_daily ADD COLUMN {col} {typ}")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS usage_aggregate (
               id INTEGER PRIMARY KEY CHECK (id = 1),
               total_gross REAL NOT NULL DEFAULT 0,
               total_net REAL NOT NULL DEFAULT 0,
               total_payable REAL NOT NULL DEFAULT 0
           )"""
    )
    conn.execute("INSERT OR IGNORE INTO usage_aggregate (id) VALUES (1)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS revenue_shares (
               id TEXT PRIMARY KEY,
               token_hash TEXT UNIQUE NOT NULL,
               creator_name TEXT NOT NULL,
               payload_json TEXT NOT NULL,
               pin_hash TEXT,
               expires_at TEXT NOT NULL,
               view_count INTEGER NOT NULL DEFAULT 0,
               max_views INTEGER NOT NULL DEFAULT 100,
               revoked INTEGER NOT NULL DEFAULT 0,
               created_at TEXT NOT NULL
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_revenue_shares_token ON revenue_shares(token_hash)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_revenue_shares_expires ON revenue_shares(expires_at)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS share_daily (
               day TEXT NOT NULL,
               ip_hash TEXT NOT NULL,
               share_count INTEGER NOT NULL DEFAULT 0,
               PRIMARY KEY (day, ip_hash)
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS oauth_states (
               state TEXT PRIMARY KEY,
               session_hash TEXT NOT NULL,
               platform TEXT NOT NULL,
               expires_at TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS platform_sessions (
               session_hash TEXT NOT NULL,
               platform TEXT NOT NULL,
               platform_user_hash TEXT NOT NULL,
               username TEXT NOT NULL,
               connected_at TEXT NOT NULL,
               expires_at TEXT NOT NULL,
               PRIMARY KEY (session_hash, platform)
           )"""
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_user_unique ON platform_sessions(platform, platform_user_hash)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS calc_proofs (
               id TEXT PRIMARY KEY,
               proof_hash TEXT UNIQUE NOT NULL,
               session_hash TEXT NOT NULL,
               payload_fingerprint TEXT NOT NULL,
               expires_at TEXT NOT NULL,
               used INTEGER NOT NULL DEFAULT 0,
               created_at TEXT NOT NULL
           )"""
    )
    rs_cols = {r[1] for r in conn.execute("PRAGMA table_info(revenue_shares)").fetchall()}
    if "session_hash" not in rs_cols:
        conn.execute("ALTER TABLE revenue_shares ADD COLUMN session_hash TEXT")


def sync_platform_admin(conn=None) -> None:
    from werkzeug.security import generate_password_hash

    email = (os.environ.get("CREATIER_ADMIN_EMAIL") or "").strip().lower()
    password = (os.environ.get("CREATIER_ADMIN_PASSWORD") or "").strip()
    if not email or not password:
        return
    hashed = generate_password_hash(password, method="scrypt")

    def _run(c):
        c.execute(
            """INSERT OR REPLACE INTO users (id, email, password, name, role, status, created_at)
               VALUES ('user-platform-1', ?, ?, '관리자', 'platform', 'active', ?)""",
            (email, hashed, _now()),
        )

    if conn is not None:
        _run(conn)
    else:
        with connect() as c:
            _run(c)


def _sync_platform_admin(conn) -> None:
    sync_platform_admin(conn)


def find_user_by_email(email: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, password, name, role, status FROM users WHERE lower(email) = ?",
            (email.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def find_user_by_id(user_id: str):
    if not user_id:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, password, name, role, status FROM users WHERE id = ?",
            (user_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def add_ledger_entry(entry: dict) -> dict:
    rid = entry.get("id") or f"led-{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """INSERT INTO ledger_entries
               (id, creator_name, platform_id, gross, platform_fee, withholding, net,
                status, earned_date, expected_deposit_date, confirmed_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rid,
                entry["creatorName"],
                entry["platformId"],
                entry["gross"],
                entry["platformFee"],
                entry["withholding"],
                entry["net"],
                entry.get("status", "pending"),
                entry["earnedDate"],
                entry.get("expectedDepositDate"),
                entry.get("confirmedAt"),
                _now(),
            ),
        )
    entry["id"] = rid
    return entry


def list_ledger(creator_name: str | None = None, limit: int = 500) -> list[dict]:
    from platforms import platform_by_id

    q = """SELECT id, creator_name, platform_id, gross, platform_fee, withholding, net,
                  status, earned_date, expected_deposit_date, confirmed_at, created_at
           FROM ledger_entries"""
    args: list = []
    if creator_name:
        q += " WHERE creator_name = ?"
        args.append(creator_name.strip())
    q += " ORDER BY earned_date DESC, created_at DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        rows = conn.execute(q, args).fetchall()
    out = []
    for r in rows:
        spec = platform_by_id(r["platform_id"])
        out.append(
            {
                "id": r["id"],
                "creatorName": r["creator_name"],
                "platformId": r["platform_id"],
                "platform": spec.name if spec else r["platform_id"],
                "gross": r["gross"],
                "platformFee": r["platform_fee"],
                "withholding": r["withholding"],
                "net": r["net"],
                "status": r["status"],
                "earnedDate": r["earned_date"],
                "expectedDepositDate": r["expected_deposit_date"],
                "confirmedAt": r["confirmed_at"],
                "createdAt": r["created_at"],
            }
        )
    return out


def get_ledger_entry(entry_id: str):
    with connect() as conn:
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return dict(row) if row else None


def confirm_ledger_entry(entry_id: str, creator_name: str, status: str = "confirmed") -> tuple[dict | None, str | None]:
    if status not in ("confirmed", "paid"):
        return None, "invalid_status"
    with connect() as conn:
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return None, "not_found"
        if row["creator_name"] != creator_name.strip():
            return None, "name_mismatch"
        conn.execute(
            "UPDATE ledger_entries SET status = ?, confirmed_at = ? WHERE id = ?",
            (status, _now(), entry_id),
        )
    return {"id": entry_id, "status": status, "creatorName": creator_name.strip()}, None


def delete_ledger_entry(entry_id: str, creator_name: str) -> tuple[bool, str | None]:
    with connect() as conn:
        row = conn.execute("SELECT creator_name FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return False, "not_found"
        if row["creator_name"] != creator_name.strip():
            return False, "name_mismatch"
        conn.execute("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))
    return True, None


def admin_overview() -> dict:
    from usage_stats import admin_usage_stats

    return admin_usage_stats()
