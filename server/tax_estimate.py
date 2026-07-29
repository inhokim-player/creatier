"""크리에이터 세금 간이 추정 (참고용 — 실제 신고는 세무 전문가와 확인)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime


# 2026 기준 종합소득세 누진 구간 (사업소득 간이)
_INCOME_BRACKETS = (
    (14_000_000, 0.06),
    (50_000_000, 0.15),
    (88_000_000, 0.24),
    (150_000_000, 0.35),
    (300_000_000, 0.38),
    (500_000_000, 0.40),
    (1_000_000_000, 0.42),
    (float("inf"), 0.45),
)

VAT_QUARTER_MONTHS = (1, 4, 7, 10)
COMPREHENSIVE_TAX_SEASON = (5,)  # 5월 확정신고


def _progressive_tax(taxable: float) -> float:
    if taxable <= 0:
        return 0.0
    tax = 0.0
    prev = 0.0
    for ceiling, rate in _INCOME_BRACKETS:
        chunk = min(taxable, ceiling) - prev
        if chunk <= 0:
            break
        tax += chunk * rate
        prev = ceiling
    return tax


def annualize_monthly(monthly_total: float, months_elapsed: int) -> float:
    if months_elapsed <= 0:
        return monthly_total * 12
    return (monthly_total / months_elapsed) * 12


def estimate_comprehensive_income_tax(
    ytd_revenue: float,
    *,
    expense_ratio: float = 0.35,
    months_elapsed: int | None = None,
) -> dict:
    """
    ytd_revenue: 올해 누적 수익 (원)
    expense_ratio: 필요경비 추정 비율 (기본 35% — 크리에이터 장비·외주 등)
    """
    today = date.today()
    elapsed = months_elapsed or today.month
    annual_revenue = annualize_monthly(ytd_revenue, elapsed) if elapsed < 12 else ytd_revenue
    taxable = max(0.0, annual_revenue * (1.0 - expense_ratio))
    national = _progressive_tax(taxable)
    local = national * 0.10
    total = national + local
    monthly_reserve = total / 12 if total else 0.0
    return {
        "annualRevenueEstimate": round(annual_revenue),
        "taxableIncomeEstimate": round(taxable),
        "nationalTaxEstimate": round(national),
        "localTaxEstimate": round(local),
        "annualTaxEstimate": round(total),
        "monthlyReserveSuggested": round(monthly_reserve),
        "expenseRatioUsed": expense_ratio,
        "disclaimer": "간이 추정치입니다. 실제 신고는 세무사·홈택스와 확인하세요.",
    }


def estimate_vat(
    quarter_revenue: float,
    *,
    vat_registered: bool = True,
) -> dict:
    if not vat_registered or quarter_revenue <= 0:
        return {
            "quarterRevenue": round(quarter_revenue),
            "vatEstimate": 0,
            "vatRegistered": vat_registered,
            "disclaimer": "부가가치세 미등록 또는 매출 없음 (간이 추정)",
        }
    vat = quarter_revenue * 0.10
    return {
        "quarterRevenue": round(quarter_revenue),
        "vatEstimate": round(vat),
        "vatRegistered": True,
        "disclaimer": "매출세액 10% 간이 추정 (매입세액 공제·면세 미반영)",
    }


def current_quarter_revenue(monthly_totals: dict[int, float], today: date | None = None) -> float:
    today = today or date.today()
    q = (today.month - 1) // 3 + 1
    start = (q - 1) * 3 + 1
    return sum(monthly_totals.get(m, 0.0) for m in range(start, start + 3))


def build_tax_alerts(
    ytd_revenue: float,
    month_revenue: float,
    monthly_totals: dict[int, float],
    *,
    expense_ratio: float = 0.35,
    vat_registered: bool = True,
    today: date | None = None,
) -> list[dict]:
    today = today or date.today()
    alerts: list[dict] = []
    comp = estimate_comprehensive_income_tax(
        ytd_revenue, expense_ratio=expense_ratio, months_elapsed=today.month
    )
    month_reserve = comp["monthlyReserveSuggested"]
    if month_reserve > 0:
        alerts.append(
            {
                "level": "info",
                "code": "monthly_tax_reserve",
                "title": "이번 달 세금 준비금 (간이 추정)",
                "message": (
                    f"이번 달 수익 기준 종합소득세·지방세 합산 "
                    f"약 {month_reserve:,}원 정도 따로 준비해 두시는 것을 권장합니다."
                ),
                "amount": month_reserve,
            }
        )

    q_rev = current_quarter_revenue(monthly_totals, today)
    vat = estimate_vat(q_rev, vat_registered=vat_registered)
    if vat["vatEstimate"] > 0 and today.month in VAT_QUARTER_MONTHS:
        _, last_day = monthrange(today.year, today.month)
        days_left = last_day - today.day
        alerts.append(
            {
                "level": "warning",
                "code": "vat_season",
                "title": "부가가치세 신고 시즌 (간이 추정)",
                "message": (
                    f"이번 분기 매출 {q_rev:,}원 기준 부가가치세 약 {vat['vatEstimate']:,}원 "
                    f"(간이 추정). 신고 마감까지 {days_left}일 남았습니다. 미리 준비하세요."
                ),
                "amount": vat["vatEstimate"],
            }
        )

    if today.month in COMPREHENSIVE_TAX_SEASON:
        alerts.append(
            {
                "level": "warning",
                "code": "comprehensive_tax_season",
                "title": "종합소득세 확정신고 시즌 (간이 추정)",
                "message": (
                    f"5월 종합소득세 신고 기간입니다. 연간 추정 세액 약 "
                    f"{comp['annualTaxEstimate']:,}원 (간이 추정). 홈택스·세무사 확인을 권장합니다."
                ),
                "amount": comp["annualTaxEstimate"],
            }
        )

    if month_revenue > 0 and month_reserve > month_revenue * 0.15:
        alerts.append(
            {
                "level": "info",
                "code": "high_tax_ratio",
                "title": "세금 부담 비율 높음",
                "message": "이번 달 수익 대비 추정 세금 비중이 큽니다. 비용 증빙·경비 정리를 검토해 보세요.",
                "amount": month_reserve,
            }
        )

    return alerts


def serialize_for_api(data: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in data.items()}
