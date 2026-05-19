"""arXiv API fetcher.

arXiv는 Atom feed로 결과를 줌. feedparser로 파싱.
API 문서: https://info.arxiv.org/help/api/user-manual.html

Rate limit: 3초에 1번 요청 권장.
"""
from __future__ import annotations

import time
from typing import Iterator

import feedparser
import requests

from paper_monitor.db import Paper
from paper_monitor.fetchers.base import contains_any, should_exclude


API_URL = "http://export.arxiv.org/api/query"
USER_AGENT = "paper-monitor/0.1 (mailto:you@example.com)"


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

    arXiv는 submittedDate로 정렬 가능. 날짜 필터는 서버단에서 안 되니
    클라이언트에서 자름.
    """
    params = {
        "search_query": _build_query(keyword, categories),
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    r = requests.get(
        API_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    feed = feedparser.parse(r.content)

    for entry in feed.entries:
        published = entry.get("published", "")[:10]  # YYYY-MM-DD
        if start_date and published < start_date:
            continue

        arxiv_id = entry.id.rsplit("/", 1)[-1]  # e.g. 2401.12345v2
        # 버전 떼기
        arxiv_id_clean = arxiv_id.split("v")[0]

        authors = [a.get("name", "") for a in entry.get("authors", [])]
        categories_list = [t.get("term") for t in entry.get("tags", [])]

        pdf_url = None
        for link in entry.get("links", []):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
                break

        yield Paper(
            id=f"arxiv:{arxiv_id_clean}",
            source="arxiv",
            title=entry.title.replace("\n", " ").strip(),
            authors=authors,
            abstract=entry.get("summary", "").strip(),
            published_date=published,
            pdf_url=pdf_url,
            landing_url=entry.get("link"),
            categories=categories_list,
            matched_keywords=[keyword],
        )


def fetch_for_keywords(
    keywords: list[str],
    categories: list[str] | None,
    exclude_keywords: list[str],
    max_per_keyword: int,
    start_date: str | None = None,
    sleep_between: float = 3.5,
) -> Iterator[Paper]:
    """여러 키워드에 대해 순차 검색 (rate-limit 친화적)."""
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
        time.sleep(sleep_between)
