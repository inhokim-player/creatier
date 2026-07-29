"""원천징수 계산 — 사업소득 3.3% · 기타소득 8.8%."""

from __future__ import annotations

RATE_BUSINESS = 0.033
RATE_OTHER = 0.088

RATE_LABELS = {
    "business": "사업소득 3.3%",
    "other": "기타소득 8.8%",
    "none": "원천징수 없음",
}


def rate_for_type(withholding_type: str | None) -> tuple[float, str]:
    if withholding_type == "business":
        return RATE_BUSINESS, "business"
    if withholding_type == "other":
        return RATE_OTHER, "other"
    return 0.0, "none"


def calc_withholding(gross: float, withholding_type: str | None) -> dict:
    """지급액(총수익) 기준 원천징수 — 수수료 차감 전."""
    amount = max(0.0, float(gross or 0))
    rate, wtype = rate_for_type(withholding_type)
    wh = round(amount * rate) if rate else 0
    if wtype == "business":
        income_tax = round(amount * 0.03)
        local_tax = round(amount * 0.003)
    elif wtype == "other":
        income_tax = round(amount * 0.08)
        local_tax = round(amount * 0.008)
    else:
        income_tax = local_tax = 0
    return {
        "withholding": wh,
        "withholdingRate": rate,
        "withholdingType": wtype,
        "withholdingLabel": RATE_LABELS.get(wtype, RATE_LABELS["none"]),
        "withholdingIncomeTax": income_tax,
        "withholdingLocalTax": local_tax,
    }


def build_withholding_summary(entries: list[dict], platform_lookup) -> dict:
    by: dict[str, dict] = {}
    total = 0
    for e in entries:
        pid = e.get("platformId") or ""
        wh = float(e.get("withholding") or 0)
        spec = platform_lookup(pid) if platform_lookup else None
        wtype = spec.withholding_type if spec else None
        rate, _ = rate_for_type(wtype)
        if pid not in by:
            by[pid] = {
                "platformId": pid,
                "platform": e.get("platform") or (spec.name if spec else pid),
                "gross": 0,
                "withholding": 0,
                "withholdingRate": rate,
                "withholdingType": wtype or "none",
                "withholdingLabel": RATE_LABELS.get(wtype or "none", RATE_LABELS["none"]),
            }
        by[pid]["gross"] += float(e.get("gross") or 0)
        by[pid]["withholding"] += wh
        total += wh
    items = sorted(by.values(), key=lambda x: -x["withholding"])
    return {
        "totalWithholding": round(total),
        "withholdingCredit": round(total),
        "byPlatform": items,
        "note": "지급액 기준 · AdSense 등 일부 플랫폼은 원천징수 없음(자진신고)",
    }
