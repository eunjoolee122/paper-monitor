"""chemRxiv public API fetcher.

엔드포인트: https://chemrxiv.org/engage/chemrxiv/public-api/v1/items
공식 문서: https://chemrxiv.org/engage/chemrxiv/public-api/documentation

GET /items?term=<query>&limit=<n>&skip=<n>
"""
from __future__ import annotations

import time
from typing import Iterator

import requests

from paper_monitor.db import Paper
from paper_monitor.fetchers.base import should_exclude


API_URL = "https://chemrxiv.org/engage/chemrxiv/public-api/v1/items"
USER_AGENT = "paper-monitor/0.1"


def search(
    keyword: str,
    max_results: int = 50,
    start_date: str | None = None,
) -> Iterator[Paper]:
    params = {
        "term": keyword,
        "limit": min(max_results, 50),  # API max는 50
        "skip": 0,
    }
    r = requests.get(
        API_URL,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("itemHits", [])

    for item in items:
        rec = item.get("item", {})
        item_id = rec.get("id")
        if not item_id:
            continue
        published = (rec.get("publishedDate") or "")[:10]
        if start_date and published and published < start_date:
            continue

        authors = [
            f"{a.get('firstName','')} {a.get('lastName','')}".strip()
            for a in rec.get("authors", [])
        ]

        # PDF URL: chemRxiv는 main asset의 URL이 있음
        pdf_url = None
        asset = rec.get("asset")
        if asset:
            pdf_url = asset.get("original", {}).get("url")

        categories = []
        for cat in rec.get("categories", []):
            name = cat.get("name")
            if name:
                categories.append(name)

        doi = rec.get("doi")
        landing = f"https://doi.org/{doi}" if doi else None

        yield Paper(
            id=f"chemrxiv:{item_id}",
            source="chemrxiv",
            title=(rec.get("title") or "").strip(),
            authors=authors,
            abstract=(rec.get("abstract") or "").strip(),
            published_date=published or "",
            pdf_url=pdf_url,
            landing_url=landing,
            categories=categories,
            matched_keywords=[keyword],
        )


def fetch_for_keywords(
    keywords: list[str],
    exclude_keywords: list[str],
    max_per_keyword: int,
    start_date: str | None = None,
    sleep_between: float = 1.0,
) -> Iterator[Paper]:
    for kw in keywords:
        print(f"  [chemrxiv] '{kw}' ...", flush=True)
        try:
            for paper in search(kw, max_per_keyword, start_date):
                blob = f"{paper.title} {paper.abstract}"
                if should_exclude(blob, exclude_keywords):
                    continue
                yield paper
        except Exception as e:
            print(f"    error: {e}", flush=True)
        time.sleep(sleep_between)
