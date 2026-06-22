"""arXiv API fetcher.

`arxiv` 라이브러리를 사용 — Client가 rate-limit 백오프 / 페이지네이션 / 재시도(429·5xx)
까지 알아서 처리한다. raw HTTP 호출을 직접 하지 않는 이유:
직접 requests를 쓰면 arxiv 서버 부하 패턴(짧은 윈도우 폭주)에서 429를 받게 됨.

API 문서: https://info.arxiv.org/help/api/user-manual.html
"""
from __future__ import annotations

from typing import Iterator

import arxiv

from paper_monitor.db import Paper
from paper_monitor.fetchers.base import should_exclude


# 모듈 단위 단일 Client — 모든 호출이 같은 인스턴스를 써야 delay/재시도가 누적 일관됨.
_CLIENT = arxiv.Client(
    page_size=100,
    delay_seconds=10.0,   # arxiv 권장 최소 요청 간격
    num_retries=5,       # 429 / 5xx 자동 백오프
)


def _build_query(keyword: str, categories: list[str] | None) -> str:
    """all:keyword AND (cat:q-bio.BM OR cat:cs.LG OR ...)"""
    parts = [f'all:"{keyword}"']
    if categories:
        cats = " OR ".join(f"cat:{c}" for c in categories)
        parts.append(f"({cats})")
    return " AND ".join(parts)


def search(
    keyword: str,
    categories: list[str] | None = None,
    max_results: int = 100,
    start_date: str | None = None,
) -> Iterator[Paper]:
    """arXiv에서 키워드로 검색.

    submittedDate 정렬. 날짜 필터는 API에 없으니 클라이언트에서 자름.
    """
    s = arxiv.Search(
        query=_build_query(keyword, categories),
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    for r in _CLIENT.results(s):
        published = r.published.date().isoformat()  # YYYY-MM-DD
        if start_date and published < start_date:
            continue

        # entry_id 예: "http://arxiv.org/abs/2401.12345v2" -> "2401.12345"
        arxiv_id = r.entry_id.rsplit("/", 1)[-1]
        arxiv_id_clean = arxiv_id.split("v")[0]

        yield Paper(
            id=f"arxiv:{arxiv_id_clean}",
            source="arxiv",
            title=r.title.replace("\n", " ").strip(),
            authors=[a.name for a in r.authors],
            abstract=(r.summary or "").strip(),
            published_date=published,
            pdf_url=r.pdf_url,
            landing_url=r.entry_id,
            categories=list(r.categories),
            matched_keywords=[keyword],
        )


def fetch_for_keywords(
    keywords: list[str],
    categories: list[str] | None,
    exclude_keywords: list[str],
    max_per_keyword: int,
    start_date: str | None = None,
    sleep_between: float = 0.0,
) -> Iterator[Paper]:
    """여러 키워드 순차 검색.

    rate-limit / 재시도는 _CLIENT가 처리하므로 호출자 sleep은 보통 불필요.
    sleep_between은 호환을 위해 시그니처에만 남겨둠 (현재는 무시).
    """
    del sleep_between  # 의도적으로 사용 안 함 — Client.delay_seconds가 대체

    for kw in keywords:
        print(f"  [arxiv] '{kw}' ...", flush=True)
        try:
            for paper in search(kw, categories, max_per_keyword, start_date):
                blob = f"{paper.title} {paper.abstract}"
                if should_exclude(blob, exclude_keywords):
                    continue
                yield paper
        except Exception as e:
            print(f"    error: {e}", flush=True)
