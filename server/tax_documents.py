"""플랫폼·세무 신고별 준비 서류 (크리에이터 · 홈택스 · 세무사 제출 기준)."""

from __future__ import annotations

# where: 어디서 받는지 / when: 언제 필요한지

COMMON_DOCS = [
    {
        "id": "bank-year",
        "title": "입금 통장 거래내역 (연간)",
        "where": "은행 앱 · 인터넷뱅킹 → 거래내역 → Excel/PDF 저장",
        "when": "플랫폼별 입금액 대조 · 종소세 수입 확인",
        "desc": "Google, TikTok, 브랜드 등 송금자명이 보이게 1월~12월",
        "required": True,
    },
    {
        "id": "expense-receipts",
        "title": "경비 영수증·세금계산서",
        "where": "촬영 장비·구독(Adobe 등)·외주·출장·통신비",
        "when": "종소세 필요경비 · 부가세 매입세액",
        "desc": "카드매출전표, 현금영수증, 세금계산서 원본 보관",
        "required": True,
    },
    {
        "id": "id-refund",
        "title": "신분증 · 환급계좌 통장",
        "where": "본인 신분증, 환급받을 본인 명의 계좌",
        "when": "홈택스 종소세·부가세 신고·환급",
        "desc": "타인 명의 계좌 불가",
        "required": True,
    },
    {
        "id": "income-summary",
        "title": "플랫폼별 연간 수입 합산표",
        "where": "플랫폼 정산서·입금 내역으로 직접 Excel 작성",
        "when": "종소세 수입금액 기재 · 세무사 전달",
        "desc": "플랫폼별 총수익·수수료·순수익·입금일 정리",
        "required": True,
    },
]

PLATFORM_DOCS: dict[str, list[dict]] = {
    "youtube_ads": [
        {
            "id": "yt-studio-export",
            "title": "YouTube Studio 수익 리포트",
            "where": "studio.youtube.com → 수익 창출 → Analytics → 기간 연간 → 내보내기(CSV/PDF)",
            "when": "월별 광고 수익 확인 · AdSense 정산 대조",
            "desc": "Estimated revenue, RPM, 조회수 포함 리포트",
            "required": True,
        },
        {
            "id": "yt-adsense-payments",
            "title": "Google AdSense 지급 내역",
            "where": "adsense.google.com → 지급 → 거래",
            "when": "실제 입금액 확인 (YouTube Studio와 차이 있을 수 있음)",
            "desc": "지급일·지급액·보류금액 확인",
            "required": True,
        },
        {
            "id": "yt-adsense-tax",
            "title": "AdSense 세금 정보 (W-8BEN 등)",
            "where": "AdSense → 설정 → 지급 → 미국 세금 정보",
            "when": "해외(구글) 소득 신고 · 원천징수율 확인",
            "desc": "한국 거주자 W-8BEN 제출 여부 확인",
            "required": True,
        },
        {
            "id": "yt-bank-match",
            "title": "AdSense 입금 통장 내역",
            "where": "통장 (송금자: Google Ireland / Google Asia Pacific 등)",
            "when": "수입금액 = 실제 입금액 + 미지급금",
            "desc": "외화 입금 시 환율 적용일·원화 환산액 메모",
            "required": True,
        },
        {
            "id": "yt-fx",
            "title": "외화 입금 환율 자료",
            "where": "은행 환전 내역 또는 한국은행 환율 (입금일 기준)",
            "when": "외화 AdSense 입금 시 종소세 원화 환산",
            "desc": "홈택스·세무사가 입금일 환율 적용",
            "required": False,
        },
    ],
    "instagram": [
        {
            "id": "ig-branded-contract",
            "title": "브랜디드·릴스 협찬 계약서",
            "where": "브랜드·에이전시와 체결한 계약 PDF/이메일",
            "when": "건별 수입 발생 시 · 분쟁 대비",
            "desc": "금액·지급일·2차 사용·독점 조항 확인",
            "required": True,
        },
        {
            "id": "ig-invoice-out",
            "title": "발행한 세금계산서 (매출)",
            "where": "홈택스 → 전자세금계산서 (사업자인 경우)",
            "when": "부가세 신고 · 브랜드에 발행분",
            "desc": "사업자 미등록 시 인보이스·계약서로 대체",
            "required": False,
        },
        {
            "id": "ig-invoice-in",
            "title": "받은 세금계산서 (경비·매입)",
            "where": "장비·스튜디오·외주 업체",
            "when": "부가세 매입세액 공제",
            "desc": "사업자등록 후 매입분 공제 가능",
            "required": False,
        },
        {
            "id": "ig-bank",
            "title": "브랜드·MCN 입금 확인",
            "where": "통장 (송금자: 브랜드명·에이전시명)",
            "when": "계약금액과 입금액 대조",
            "desc": "건별 메모(어떤 캠페인) 남기기",
            "required": True,
        },
        {
            "id": "ig-post-proof",
            "title": "게시·이행 증빙",
            "where": "업로드 URL, Insights 캡처, 계약 이행 확인 메일",
            "when": "수입 인정·분쟁 시",
            "desc": "릴스·피드·스토리 게시 스크린샷",
            "required": False,
        },
        {
            "id": "ig-reels-bonus",
            "title": "Instagram 보너스·릴스 수익 내역",
            "where": "Instagram 앱 → Professional dashboard → Insights (해당 시)",
            "when": "Meta 직접 지급 수익 있는 경우",
            "desc": "프로그램별 정산 주기 확인",
            "required": False,
        },
    ],
    "tiktok": [
        {
            "id": "tt-creator-rewards",
            "title": "TikTok Creator Rewards / 프로그램 수익",
            "where": "TikTok Studio → Analytics → Monetization / Creator Rewards",
            "when": "크리에이터 프로그램 정산 확인",
            "desc": "월별 estimated rewards, 조건 충족 여부",
            "required": True,
        },
        {
            "id": "tt-live-gifts",
            "title": "LIVE 선물·구독 수익 내역",
            "where": "TikTok Studio → LIVE → Revenue / Wallet",
            "when": "라이브 수익 비중 있을 때",
            "desc": "플랫폼 수수료(~50%) 차감 후 순수익",
            "required": False,
        },
        {
            "id": "tt-payout",
            "title": "TikTok 정산(Payout) 명세",
            "where": "TikTok Studio → Balance / Payout history",
            "when": "실제 입금액 대조",
            "desc": "최소 출금액·정산 주기(월 1~2회) 확인",
            "required": True,
        },
        {
            "id": "tt-bank",
            "title": "TikTok 입금 통장 내역",
            "where": "통장 (TikTok Pte. Ltd / ByteDance 등)",
            "when": "수입금액 확인",
            "desc": "외화 입금 시 환율 메모",
            "required": True,
        },
        {
            "id": "tt-brand-deal",
            "title": "TikTok Creator Marketplace 계약",
            "where": "TCM(TikTok Creator Marketplace) 브랜드 deal 계약",
            "when": "플랫폼 경유 협찬",
            "desc": "브랜드 deal 금액·지급 경로",
            "required": False,
        },
    ],
    "sponsorship": [
        {
            "id": "sp-contract",
            "title": "협찬·PPL·원고료 계약서",
            "where": "브랜드·광고대행사 계약 PDF",
            "when": "수입 발생 건마다",
            "desc": "원천징수 주체(지급자) 명시 확인",
            "required": True,
        },
        {
            "id": "sp-wh-receipt",
            "title": "원천징수영수증",
            "where": "지급처(브랜드·대행사) 발급",
            "when": "종소세 원천징수세액 공제 (필수)",
            "desc": "사업소득 3.3% 또는 기타소득 — 소득구분 확인",
            "required": True,
        },
        {
            "id": "sp-tax-invoice",
            "title": "세금계산서 (협찬·광고)",
            "where": "발행(매출) 또는 수취(매입) — 홈택스",
            "when": "부가세 포함 거래 · 사업자",
            "desc": "공급가액·부가세·원천징수 별도 확인",
            "required": False,
        },
        {
            "id": "sp-agency-fee",
            "title": "에이전시·MCN 수수료 명세",
            "where": "MCN 정산서, 수수료 3~10% 차감 내역",
            "when": "총액 vs 실수령액 대조",
            "desc": "수수료도 경비 처리 가능(증빙 필요)",
            "required": False,
        },
        {
            "id": "sp-content-proof",
            "title": "콘텐츠 게시·납품 증빙",
            "where": "업로드 URL, 납품 확인 메일",
            "when": "수입 인정 · 계약 이행",
            "desc": "유튜브·인스타·틱톡 게시 링크",
            "required": True,
        },
    ],
}

COMPREHENSIVE_DOCS = [
    {
        "id": "comp-hometax-login",
        "title": "홈택스 종합소득세 신고",
        "where": "hometax.go.kr → 세금신고 → 종합소득세",
        "when": "매년 5월 1일 ~ 5월 31일",
        "desc": "프리랜서·사업소득 해당 시 확정신고",
        "required": True,
    },
    {
        "id": "comp-income-stmt",
        "title": "수입금액 명세서",
        "where": "홈택스 신고서 [수입금액] 란 · 별첨 Excel",
        "when": "종소세 신고",
        "desc": "플랫폼별·건별 합산 (YouTube+Instagram+TikTok+협찬)",
        "required": True,
    },
    {
        "id": "comp-expense-stmt",
        "title": "필요경비 명세·장부",
        "where": "간편장부(기준경비율) 또는 복식부기",
        "when": "종소세 신고",
        "desc": "35%·60% 기준경비율 또는 실제 경비",
        "required": True,
    },
    {
        "id": "comp-wh-credit",
        "title": "원천징수세액공제명세",
        "where": "홈택스 → 원천징수영수증 등록 · 공제신청",
        "when": "종소세 (이미 낸 3.3% 등 공제)",
        "desc": "협찬·원고료 원천징수분",
        "required": True,
    },
    {
        "id": "comp-card-deduct",
        "title": "신용카드·현금영수증 (해당 시)",
        "where": "홈택스 → MyNTS → 소득·세액공제",
        "when": "근로+사업 병행 · 공제 항목",
        "desc": "프리랜서 단독 시 해당 적을 수 있음",
        "required": False,
    },
]

VAT_DOCS = [
    {
        "id": "vat-registration",
        "title": "사업자등록증",
        "where": "홈택스 · 세무서 (연 매출 4,800만 원 초과 등)",
        "when": "부가세 과세 사업자",
        "desc": "간이과세·일반과세 구분",
        "required": True,
    },
    {
        "id": "vat-quarter-sales",
        "title": "분기 매출 합계표",
        "where": "홈택스 → 부가가치세 → 매출세액",
        "when": "1·4·7·10월 확정신고",
        "desc": "세금계산서·카드·현금영수증 매출",
        "required": True,
    },
    {
        "id": "vat-purchase",
        "title": "매입세액 공제 서류",
        "where": "경비 세금계산서·카드 매입 · 고정자산 해당 시",
        "when": "분기 부가세",
        "desc": "업종·비용별 매입 분류",
        "required": True,
    },
    {
        "id": "vat-etax",
        "title": "전자세금계산서 발급·수취 내역",
        "where": "홈택스 → 전자세금계산서 → 월별 조회",
        "when": "부가세 신고",
        "desc": "누락분 없는지 월별 확인",
        "required": True,
    },
]

FOREIGN_INCOME_DOCS = [
    {
        "id": "foreign-fx-statement",
        "title": "해외송금·외화입금 확인서",
        "where": "은행 (YouTube·TikTok 등 해외법인 송금)",
        "when": "외화 수입 있는 경우",
        "desc": "입금일·외화·원화 환산액",
        "required": False,
    },
]


def all_platform_ids() -> list[str]:
    return list(PLATFORM_DOCS.keys())


def build_document_checklist(used_platform_ids: set[str], *, vat_registered: bool) -> list[dict]:
    docs: list[dict] = []
    seen: set[str] = set()

    def add(item: dict, group: str):
        if item["id"] in seen:
            return
        seen.add(item["id"])
        docs.append({**item, "group": group})

    for d in COMMON_DOCS:
        add(d, "공통 · 전 플랫폼")

    has_foreign = bool(used_platform_ids & {"youtube_ads", "tiktok"})
    if has_foreign:
        for d in FOREIGN_INCOME_DOCS:
            add(d, "해외 플랫폼 (YouTube·TikTok)")

    for pid in sorted(used_platform_ids):
        from platforms import platform_by_id

        spec = platform_by_id(pid)
        group = spec.name if spec else pid
        for d in PLATFORM_DOCS.get(pid, []):
            add(d, group)

    for d in COMPREHENSIVE_DOCS:
        add(d, "종합소득세 (5월)")

    if vat_registered:
        for d in VAT_DOCS:
            add(d, "부가가치세 (분기)")

    return docs


def full_document_guide() -> dict:
    """전체 플랫폼 서류 가이드 (입력 없이도 참고용)."""
    from platforms import platform_by_id

    out = {"common": COMMON_DOCS, "platforms": {}, "comprehensive": COMPREHENSIVE_DOCS, "vat": VAT_DOCS}
    for pid, items in PLATFORM_DOCS.items():
        spec = platform_by_id(pid)
        out["platforms"][pid] = {"name": spec.name if spec else pid, "documents": items}
    return out
