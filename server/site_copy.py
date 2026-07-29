"""UI·이메일 문구 — creatier/data/copy.json 한 파일에서 관리."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPY_PATH = ROOT / "data" / "copy.json"


@lru_cache(maxsize=1)
def load_copy() -> dict:
    if not COPY_PATH.is_file():
        return {}
    return json.loads(COPY_PATH.read_text(encoding="utf-8"))


def get_copy(*keys: str, default: str = "") -> str:
    node = load_copy()
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key, default if key == keys[-1] else {})
    return node if isinstance(node, str) else default


def format_copy(*keys: str, default: str = "", **kwargs) -> str:
    text = get_copy(*keys, default=default)
    try:
        return text.format(**kwargs)
    except (KeyError, ValueError):
        return text
