"""Europe PMC API fetcher.

bioRxiv의 자체 API는 키워드 검색이 빈약해서 Europe PMC를 통해 검색.
Europe PMC는 bioRxiv + chemRxiv + PubMed를 통합 인덱싱.

문서: https://europepmc.org/RestfulWebService

이 fetcher는 bioRxiv preprint만 가져오도록 SRC:PPR + PUB_TYPE:Preprint 필터를 검.
"""
from __future__ import annotations

import time
from typing import Iterator

import requests

from paper_monitor.db import Paper
from paper_monitor.fetchers.base import should_exclude


API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
USER_AGENT = "paper-monitor/0.1"


def search(
    keyword: str,
    max_results: int = 100,
    start_date: str | None = None,
    sources: tuple[str, ...] = ("PPR",),  # PPR = preprint
) -> Iterator[Paper]:
    # Europe PMC query syntax
    src_filter = " OR ".join(f"SRC:{s}" for s in sources)
    date_filter = ""
    if start_date:
        # FIRST_PDATE:[2023-01-01 TO 2026-12-31]
        date_filter = f' AND FIRST_PDATE:[{start_date} TO 2099-12-31]'

    query = f'("{keyword}") AND ({src_filter}){date_filter}'

    params = {
        "query": query,
        "resultType": "core",
        "format": "json",
        "pageSize": min(max_results, 100),
    }
    r = requests.get(
        API_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("resultList", {}).get("result", [])

    for rec in results:
        # Europe PMC ID 만들기
        doi = rec.get("doi")
        pmid = rec.get("pmid")
        pmcid = rec.get("pmcid")
        source = rec.get("source", "").lower()

        # 백엔드 ID: DOI 우선, 그 다음 PMID, PMCID
        if doi:
            paper_id = f"doi:{doi}"
        elif pmid:
            paper_id = f"pmid:{pmid}"
        elif pmcid:
            paper_id = f"pmcid:{pmcid}"
        else:
            continue

        # bioRxiv 식별: bookOrReportDetails나 journalInfo에서
        # source가 PPR인 preprint는 대부분 bioRxiv/medRxiv/research square
        publisher = rec.get("bookOrReportDetails", {}).get("publisher", "")
        if "biorxiv" in publisher.lower() or "biorxiv" in (rec.get("journalTitle") or "").lower():
            src_label = "biorxiv"
        elif "medrxiv" in publisher.lower():
            src_label = "medrxiv"
        elif "chemrxiv" in publisher.lower() or "chemrxiv" in (rec.get("journalTitle") or "").lower():
            src_label = "chemrxiv"
        else:
            src_label = "preprint"

        # 저자 파싱
        authors_str = rec.get("authorString") or ""
        authors = [a.strip() for a in authors_str.split(",") if a.strip()]

        published = (rec.get("firstPublicationDate") or "")[:10]

        # PDF URL
        pdf_url = None
        for fl in rec.get("fullTextUrlList", {}).get("fullTextUrl", []):
            if fl.get("documentStyle") == "pdf":
                pdf_url = fl.get("url")
                break

        # 랜딩 URL
        landing = None
        if doi:
            landing = f"https://doi.org/{doi}"
        elif pmcid:
            landing = f"https://europepmc.org/article/PMC/{pmcid}"

        yield Paper(
            id=paper_id,
            source=src_label,
            title=(rec.get("title") or "").strip().rstrip("."),
            authors=authors,
            abstract=(rec.get("abstractText") or "").strip(),
            published_date=published,
            pdf_url=pdf_url,
            landing_url=landing,
            categories=[],
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
        print(f"  [europepmc] '{kw}' ...", flush=True)
        try:
            for paper in search(kw, max_per_keyword, start_date):
                blob = f"{paper.title} {paper.abstract}"
                if should_exclude(blob, exclude_keywords):
                    continue
                yield paper
        except Exception as e:
            print(f"    error: {e}", flush=True)
        time.sleep(sleep_between)
