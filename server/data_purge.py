"""만료 데이터 즉시 파기."""

from __future__ import annotations

from db import _now, connect


def purge_expired() -> None:
    now = _now()
    with connect() as conn:
        conn.execute("DELETE FROM oauth_states WHERE expires_at < ?", (now,))
        conn.execute("DELETE FROM calc_proofs WHERE expires_at < ? OR used = 1", (now,))
        conn.execute("DELETE FROM platform_sessions WHERE expires_at < ?", (now,))
        conn.execute("DELETE FROM revenue_shares WHERE expires_at < ?", (now,))
