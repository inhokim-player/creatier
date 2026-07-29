"""세무사·홈택스 제출용 서류 팩."""

from __future__ import annotations

from datetime import date


def build_filing_pack(creator_name: str, entries: list[dict], tax_report: dict) -> dict:
    today = date.today().isoformat()
    year = date.today().year
    year_entries = [e for e in entries if e["earnedDate"].startswith(str(year))]

    revenue_lines = [
        {
            "일자": e["earnedDate"],
            "플랫폼": e["platform"],
            "총수익": e["gross"],
            "플랫폼수수료": e["platformFee"],
            "원천징수": e["withholding"],
            "순수익": e["net"],
        }
        for e in sorted(year_entries, key=lambda x: x["earnedDate"])
    ]

    s = tax_report["summary"]
    docs = tax_report.get("documents") or []

    return {
        "generatedAt": today,
        "creatorName": creator_name,
        "귀속연도": year,
        "수익요약": {
            "연간총수익": s["ytdGross"],
            "연간순수익": s["ytdNet"],
            "플랫폼수수료합계": s["ytdFees"],
            "원천징수합계": s["ytdWithholding"],
        },
        "세금예상": {
            "종합소득세_추정": s["comprehensiveTotal"],
            "원천징수_공제": s["withholdingCredit"],
            "종합소득세_납부예상": s["comprehensivePayable"],
            "부가가치세_연간추정": s["annualVat"],
            "합계_납부예상": s["totalPayable"],
            "월준비금_권장": s["monthlyReserve"],
            "계산기준": s.get("taxBasis", "순수익 기준"),
        },
        "플랫폼별집계": tax_report.get("byPlatform") or [],
        "수익내역": revenue_lines,
        "준비서류_체크리스트": [
            {
                "구분": d["group"],
                "항목": d["title"],
                "어디서": d.get("where", ""),
                "언제": d.get("when", ""),
                "설명": d.get("desc", ""),
            }
            for d in docs
        ],
        "신고일정": tax_report.get("filingCalendar") or [],
        "disclaimer": tax_report.get("disclaimer"),
    }
