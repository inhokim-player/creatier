"""수익 · 경비 · 원천징수 · 정산 데모 (대표 4플랫폼)."""

from __future__ import annotations

from datetime import date, timedelta

from platforms import net_after_fee, platform_by_id


def demo_profile() -> dict:
    return {
        "id": "creator-demo",
        "name": "데모 크리에이터",
        "email": "creator@example.com",
        "businessType": "freelancer",
        "vatRegistered": True,
        "expenseRatio": 0.35,
    }


def demo_revenue_entries() -> list[dict]:
    today = date.today()
    specs = [
        ("youtube_ads", 7_500_000, "paid", -35),
        ("youtube_ads", 6_800_000, "paid", -65),
        ("youtube_ads", 8_100_000, "accrued", -5),
        ("instagram", 1_200_000, "paid", -42),
        ("instagram", 890_000, "accrued", -8),
        ("tiktok", 620_000, "accrued", -10),
        ("tiktok", 480_000, "pending", 12),
        ("sponsorship", 3_500_000, "accrued", -8),
        ("sponsorship", 2_000_000, "pending", 25),
    ]
    rows = []
    for pid, gross, status, day_offset in specs:
        spec = platform_by_id(pid)
        d = today + timedelta(days=day_offset)
        lag = spec.settlement_lag_days if spec else 30
        calc = net_after_fee(gross, pid)
        rows.append(
            {
                "id": f"rev-{pid}-{d.isoformat()}-{gross}",
                "platformId": pid,
                "platform": spec.name if spec else pid,
                "gross": gross,
                "platformFee": calc["platformFee"],
                "withholding": calc["withholding"],
                "net": calc["net"],
                "status": status,
                "earnedDate": d.isoformat(),
                "expectedDepositDate": (d + timedelta(days=lag)).isoformat(),
                "source": "manual" if spec and spec.api_status == "manual" else "sync",
            }
        )
    return rows


def demo_expenses() -> list[dict]:
    today = date.today()
    return [
        {"id": "exp-1", "category": "장비", "label": "촬영 조명", "amount": 450_000, "date": (today - timedelta(days=12)).isoformat(), "deductible": True},
        {"id": "exp-2", "category": "외주", "label": "편집 외주", "amount": 800_000, "date": (today - timedelta(days=20)).isoformat(), "deductible": True},
        {"id": "exp-3", "category": "구독", "label": "Adobe · 음원", "amount": 89_000, "date": (today - timedelta(days=5)).isoformat(), "deductible": True},
    ]


def demo_withholding_ledger() -> list[dict]:
    return [
        {
            "id": "wh-1",
            "platformId": "sponsorship",
            "platform": "협찬 · 광고",
            "gross": 3_500_000,
            "rate": 0.033,
            "amount": 115_500,
            "date": "2026-07-08",
            "payer": "브랜드A (원천)",
            "status": "reported",
        },
        {
            "id": "wh-2",
            "platformId": "sponsorship",
            "platform": "협찬 · 광고",
            "gross": 2_000_000,
            "rate": 0.033,
            "amount": 66_000,
            "date": "2026-07-22",
            "payer": "브랜드B (예정)",
            "status": "pending",
        },
    ]


def aggregate_dashboard(entries: list[dict], expenses: list[dict], profile: dict) -> dict:
    today = date.today()
    month, year = today.month, today.year

    def in_month(d_str: str) -> bool:
        d = date.fromisoformat(d_str)
        return d.year == year and d.month == month

    month_entries = [e for e in entries if in_month(e["earnedDate"])]
    month_gross = sum(e["gross"] for e in month_entries)
    month_net = sum(e["net"] for e in month_entries)
    month_fees = sum(e["platformFee"] for e in month_entries)
    month_wh = sum(e["withholding"] for e in month_entries)

    ytd_gross = sum(e["gross"] for e in entries if date.fromisoformat(e["earnedDate"]).year == year)
    ytd_net = sum(e["net"] for e in entries if date.fromisoformat(e["earnedDate"]).year == year)
    unpaid = sum(e["net"] for e in entries if e["status"] in ("accrued", "pending", "confirmed", "recorded"))
    paid = sum(e["net"] for e in entries if e["status"] == "paid")

    by_platform: dict[str, dict] = {}
    for e in entries:
        pid = e["platformId"]
        if pid not in by_platform:
            by_platform[pid] = {"platformId": pid, "platform": e["platform"], "gross": 0, "net": 0, "fee": 0}
        by_platform[pid]["gross"] += e["gross"]
        by_platform[pid]["net"] += e["net"]
        by_platform[pid]["fee"] += e["platformFee"]

    monthly_totals: dict[int, float] = {}
    for e in entries:
        d = date.fromisoformat(e["earnedDate"])
        if d.year == year:
            monthly_totals[d.month] = monthly_totals.get(d.month, 0) + e["net"]

    recent_months = sorted(monthly_totals.keys())[-3:]
    forecast_next = round(sum(monthly_totals[m] for m in recent_months) / len(recent_months)) if recent_months else 0

    expense_month = sum(x["amount"] for x in expenses if in_month(x["date"]))
    expense_ytd = sum(x["amount"] for x in expenses if date.fromisoformat(x["date"]).year == year)

    upcoming = sorted(
        [e for e in entries if e["status"] in ("accrued", "pending", "confirmed")],
        key=lambda x: x.get("expectedDepositDate", ""),
    )[:8]

    return {
        "monthGross": month_gross,
        "monthNet": month_net,
        "monthFees": month_fees,
        "monthWithholding": month_wh,
        "monthRevenue": month_net,
        "ytdGross": ytd_gross,
        "ytdNet": ytd_net,
        "ytdRevenue": ytd_net,
        "unpaidTotal": unpaid,
        "paidTotal": paid,
        "forecastNextMonth": forecast_next,
        "byPlatform": sorted(by_platform.values(), key=lambda x: -x["net"]),
        "monthlyTotals": monthly_totals,
        "upcomingDeposits": upcoming,
        "expensesMonth": expense_month,
        "expensesYtd": expense_ytd,
        "profile": profile,
    }
