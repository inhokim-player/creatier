"""플랫폼별 세금·서류 안내 — YouTube · Instagram · TikTok · 협찬."""

from __future__ import annotations

from dataclasses import dataclass

from withholding import calc_withholding


@dataclass(frozen=True)
class PlatformSpec:
    id: str
    name: str
    category: str
    fee_rate: float
    settlement_lag_days: int
    settlement_label: str
    withholding_type: str | None  # business | other | None
    api_status: str
    tax_note: str
    doc_hint: str
    notes: str = ""

    @property
    def withholding_default(self) -> float:
        from withholding import RATE_BUSINESS, RATE_OTHER

        if self.withholding_type == "business":
            return RATE_BUSINESS
        if self.withholding_type == "other":
            return RATE_OTHER
        return 0.0


PLATFORMS: tuple[PlatformSpec, ...] = (
    PlatformSpec(
        "youtube_ads",
        "YouTube 광고",
        "ad",
        0.45,
        30,
        "매월 21~26일 (전월 확정)",
        None,
        "manual",
        "AdSense 정산 — 원천징수 없음, 종합소득세 자진신고.",
        "YouTube Studio 수익 리포트 · AdSense 정산서 · 입금 통장내역",
        "YouTube Partner Program 광고 수익",
    ),
    PlatformSpec(
        "instagram",
        "Instagram",
        "social",
        0.05,
        30,
        "릴스·브랜디드 (계약별)",
        "business",
        "manual",
        "브랜디드·릴스 수익 — 사업소득 원천징수 3.3% (지급자 공제).",
        "브랜디드 계약서 · 원천징수영수증 · 입금 확인",
        "릴스 보너스 · 브랜디드 콘텐츠",
    ),
    PlatformSpec(
        "tiktok",
        "TikTok",
        "social",
        0.50,
        28,
        "월 1~2회 정산",
        "business",
        "manual",
        "크리에이터 수익 — 사업소득 원천징수 3.3% 간이 적용.",
        "TikTok Studio 정산 · 원천징수영수증 · 입금 내역",
        "크리에이터 프로그램 · 라이브 선물",
    ),
    PlatformSpec(
        "sponsorship",
        "협찬 · 광고",
        "sponsorship",
        0.03,
        30,
        "계약별",
        "business",
        "manual",
        "협찬·원고료 — 사업소득 원천징수 3.3%. 원천징수영수증 필수.",
        "협찬 계약서 · 원천징수영수증 · 세금계산서",
        "브랜드 협찬 · PPL · 원고료",
    ),
)


def platform_by_id(platform_id: str) -> PlatformSpec | None:
    return next((p for p in PLATFORMS if p.id == platform_id), None)


def platform_list() -> list[dict]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "feeRate": p.fee_rate,
            "feePercent": round(p.fee_rate * 100, 1),
            "settlementLagDays": p.settlement_lag_days,
            "settlementLabel": p.settlement_label,
            "withholdingType": p.withholding_type,
            "withholdingDefault": p.withholding_default,
            "withholdingLabel": (
                "3.3%" if p.withholding_type == "business" else "8.8%" if p.withholding_type == "other" else "없음"
            ),
            "apiStatus": p.api_status,
            "taxNote": p.tax_note,
            "docHint": p.doc_hint,
            "notes": p.notes,
        }
        for p in PLATFORMS
    ]


def net_after_fee(gross: float, platform_id: str) -> dict:
    spec = platform_by_id(platform_id)
    rate = spec.fee_rate if spec else 0.0
    fee = round(gross * rate)
    wh_info = calc_withholding(gross, spec.withholding_type if spec else None)
    withholding = wh_info["withholding"]
    net = gross - fee - withholding
    return {
        "gross": round(gross),
        "platformFee": fee,
        "withholding": withholding,
        "withholdingRate": wh_info["withholdingRate"],
        "withholdingType": wh_info["withholdingType"],
        "withholdingLabel": wh_info["withholdingLabel"],
        "withholdingIncomeTax": wh_info["withholdingIncomeTax"],
        "withholdingLocalTax": wh_info["withholdingLocalTax"],
        "net": round(net),
        "feeRate": rate,
        "platformId": platform_id,
    }
