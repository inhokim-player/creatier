"""활동명 악용 방지 — 유명인 보호 · PIN · 세션 토큰."""

from __future__ import annotations

import re

# 유명 활동명 (정규화 후 exact match) — 타인이 저장·주작 불가, 미리보기만 가능
RESERVED_NAMES: frozenset[str] = frozenset(
    {
        "감스트",
        "gamst",
        "침착맨",
        "우왁굳",
        "김도",
        "머독",
        "양띵",
        "대도서관",
        "인피쉰",
        "키성태",
        "랄로",
        "오킹",
        "케이",
        "피식대학",
        "슈카",
        "슈카월드",
        "itsub",
        "잇섭",
        "카라",
        "라이또",
        "히밥",
        "똘킹",
        "김블루",
        "풍월량",
        "코마",
        "이병욱",
        "쯔양",
        "햄지",
        "빠니보틀",
        "장성규",
        "김계란",
        "철구",
        "백종원",
        "이재명",
        "윤석열",
        "bts",
        "방탄",
        "블랙핑크",
        "iu",
        "아이유",
        "admin",
        "관리자",
        "root",
    }
)


def normalize_creator_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[\s_\-·.]+", "", s)
    return s


def is_reserved_name(name: str) -> bool:
    norm = normalize_creator_name(name)
    if not norm:
        return False
    if norm in RESERVED_NAMES:
        return True
    for reserved in RESERVED_NAMES:
        r = normalize_creator_name(reserved)
        if len(r) >= 3 and norm.startswith(r) and len(norm) <= len(r) + 6:
            return True
    return False


def pin_valid(pin: str) -> bool:
    p = (pin or "").strip()
    return 4 <= len(p) <= 32
