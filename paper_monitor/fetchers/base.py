"""모든 fetcher가 공유하는 유틸."""
from __future__ import annotations

import re
from typing import Iterable


def matches_keyword(text: str, keyword: str) -> bool:
    """대소문자 무시, 단어 경계 고려한 매칭."""
    if not text or not keyword:
        return False
    pattern = re.escape(keyword.lower())
    return re.search(rf"\b{pattern}\b", text.lower()) is not None


def contains_any(text: str, keywords: Iterable[str]) -> list[str]:
    """포함된 키워드 리스트 반환."""
    if not text:
        return []
    hits = []
    for kw in keywords:
        if matches_keyword(text, kw):
            hits.append(kw)
    return hits


def should_exclude(text: str, exclude_keywords: Iterable[str]) -> bool:
    return bool(contains_any(text, exclude_keywords))
