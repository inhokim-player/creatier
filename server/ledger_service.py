"""대시보드 집계 — 수익 입력 + 세금·부가세 계산."""

from __future__ import annotations

from demo_data import aggregate_dashboard
from tax_report import build_tax_report


def build_dashboard(
    creator_name: str,
    entries: list[dict],
    *,
    vat_registered: bool = False,
) -> dict:
    profile = {"name": creator_name, "vatRegistered": vat_registered}
    agg = aggregate_dashboard(entries, [], profile)

    tax = build_tax_report(
        entries,
        agg["monthlyTotals"],
        creator_name=creator_name,
        vat_registered=vat_registered,
    )

    year_entries = sorted(entries, key=lambda e: (e.get("earnedDate", ""), e.get("createdAt", "")), reverse=True)

    return {
        "creatorName": creator_name,
        "summary": {
            **agg,
            "entryCount": len(entries),
            **tax["summary"],
        },
        "entries": year_entries,
        "byPlatform": tax["byPlatform"],
        "withholding": tax["withholding"],
        "monthlyTotals": agg["monthlyTotals"],
        "taxReport": tax,
    }
