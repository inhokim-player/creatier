"""세금 납부 예상 · 플랫폼별 안내 · 서류 준비 체크리스트."""

from __future__ import annotations

from datetime import date

from platforms import platform_by_id
from withholding import build_withholding_summary
from tax_documents import build_document_checklist, full_document_guide
from tax_estimate import build_tax_alerts, current_quarter_revenue, estimate_comprehensive_income_tax, estimate_vat

FILING_CALENDAR = [
    {"month": 1, "label": "1월", "task": "연말정산·4분기 부가세 (사업자)", "code": "vat_q4"},
    {"month": 4, "label": "4월", "task": "1분기 부가세 확정신고 (사업자)", "code": "vat_q1"},
    {"month": 5, "label": "5월", "task": "종합소득세 확정신고 (5/1~5/31)", "code": "comprehensive"},
    {"month": 7, "label": "7월", "task": "2분기 부가세 확정신고 (사업자)", "code": "vat_q2"},
    {"month": 10, "label": "10월", "task": "3분기 부가세 확정신고 (사업자)", "code": "vat_q3"},
]


def _platform_ids_used(entries: list[dict]) -> set[str]:
    return {e["platformId"] for e in entries if e.get("platformId")}


def build_platform_tax_summary(entries: list[dict]) -> list[dict]:
    by: dict[str, dict] = {}
    for e in entries:
        pid = e["platformId"]
        if pid not in by:
            spec = platform_by_id(pid)
            by[pid] = {
                "platformId": pid,
                "platform": e.get("platform") or (spec.name if spec else pid),
                "gross": 0,
                "fee": 0,
                "withholding": 0,
                "net": 0,
                "count": 0,
                "taxNote": spec.tax_note if spec else "",
                "docHint": spec.doc_hint if spec else "",
            }
        by[pid]["gross"] += e["gross"]
        by[pid]["fee"] += e["platformFee"]
        by[pid]["withholding"] += e["withholding"]
        by[pid]["net"] += e["net"]
        by[pid]["count"] += 1
    return sorted(by.values(), key=lambda x: -x["net"])


def build_tax_report(
    entries: list[dict],
    monthly_totals: dict[int, float],
    *,
    creator_name: str = "",
    vat_registered: bool = False,
) -> dict:
    today = date.today()
    year = today.year

    ytd_entries = [e for e in entries if e["earnedDate"].startswith(str(year))]
    ytd_net = sum(e["net"] for e in ytd_entries)
    ytd_gross = sum(e["gross"] for e in ytd_entries)
    ytd_fees = sum(e["platformFee"] for e in ytd_entries)
    ytd_withholding = sum(e["withholding"] for e in ytd_entries)
    # 원천징수는 선납세 — 과세 수입에서는 차감하지 않음 (실수령만 차감)
    ytd_taxable = ytd_gross - ytd_fees

    month_net = sum(
        e["net"]
        for e in ytd_entries
        if date.fromisoformat(e["earnedDate"]).month == today.month
    )

    monthly_taxable: dict[int, float] = {}
    for e in ytd_entries:
        d = date.fromisoformat(e["earnedDate"])
        monthly_taxable[d.month] = monthly_taxable.get(d.month, 0) + (
            e["gross"] - e["platformFee"]
        )

    # 종소세: 원천징수 전 수입 기준 추정 → 이미 납부한 원천징수 공제
    comp = estimate_comprehensive_income_tax(
        ytd_taxable, expense_ratio=0.0, months_elapsed=today.month
    )
    q_rev = current_quarter_revenue(monthly_taxable, today)
    vat = estimate_vat(q_rev, vat_registered=vat_registered)
    annual_vat = estimate_vat(sum(monthly_taxable.values()), vat_registered=vat_registered)

    withholding_credit = ytd_withholding
    comp_payable = max(0, comp["annualTaxEstimate"] - withholding_credit)
    vat_payable = annual_vat["vatEstimate"] if vat_registered else 0
    total_payable = comp_payable + vat_payable

    alerts = build_tax_alerts(
        ytd_taxable, month_net, monthly_taxable,
        expense_ratio=0.0, vat_registered=vat_registered,
    )

    upcoming_filing = [
        f for f in FILING_CALENDAR
        if f["month"] >= today.month or f["month"] == 5
    ][:3]

    used = _platform_ids_used(ytd_entries)
    wh_summary = build_withholding_summary(ytd_entries, platform_by_id)

    return {
        "creatorName": creator_name,
        "year": year,
        "withholding": wh_summary,
        "summary": {
            "ytdGross": round(ytd_gross),
            "ytdNet": round(ytd_net),
            "ytdTaxable": round(ytd_taxable),
            "ytdFees": round(ytd_fees),
            "ytdWithholding": round(ytd_withholding),
            "comprehensiveTax": comp["annualTaxEstimate"],
            "localTax": comp["localTaxEstimate"],
            "comprehensiveTotal": comp["annualTaxEstimate"],
            "withholdingCredit": round(withholding_credit),
            "comprehensivePayable": round(comp_payable),
            "quarterVat": vat["vatEstimate"],
            "annualVat": round(vat_payable),
            "totalPayable": round(total_payable),
            "monthlyReserve": comp["monthlyReserveSuggested"],
            "vatRegistered": vat_registered,
            "taxBasis": "실수령 = 총수익 − 수수료 − 원천징수 · 종소세는 원천징수 전 수입 기준 추정 후 원천징수 공제",
        },
        "comprehensive": comp,
        "vat": vat,
        "annualVat": annual_vat,
        "byPlatform": build_platform_tax_summary(ytd_entries),
        "documents": build_document_checklist(used, vat_registered=vat_registered),
        "documentGuide": full_document_guide(),
        "filingCalendar": upcoming_filing,
        "alerts": alerts,
        "disclaimer": "간이 추정치입니다. 사업 형태·공제·감면에 따라 달라집니다. 세무사·홈택스로 최종 확인하세요.",
    }
