"""백필 스크립트: queries.yaml의 모든 키워드로 과거 N년치 논문 메타데이터 수집.

사용:
    python scripts/backfill.py

처음 한 번 실행하면 papers.sqlite에 메타데이터가 채워짐.
이후엔 scripts/fetch_new.py로 incremental 업데이트.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 import path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config, load_queries
from paper_monitor.db import connect, init_db, upsert_paper
from paper_monitor.fetchers import arxiv, chemrxiv, europepmc


def main() -> None:
    cfg = load_config()
    q = load_queries()

    db_path = cfg["db_path"]
    init_db(db_path)

    start_date = q.get("date_range", {}).get("start")
    keywords = q["core_keywords"]
    exclude = q.get("exclude_keywords", [])
    arxiv_cats = q.get("arxiv_categories")
    limits = q.get("limits", {})

    fetched_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    n_new_total = 0
    n_seen_total = 0

    # --- arXiv ---
    print("=== arXiv ===")
    with connect(db_path) as conn:
        for paper in arxiv.fetch_for_keywords(
            keywords,
            categories=arxiv_cats,
            exclude_keywords=exclude,
            max_per_keyword=limits.get("arxiv_per_keyword", 100),
            start_date=start_date,
        ):
            is_new = upsert_paper(conn, paper, fetched_at)
            if is_new:
                n_new_total += 1
            else:
                n_seen_total += 1

    # --- chemRxiv ---
    print("\n=== chemRxiv ===")
    with connect(db_path) as conn:
        for paper in chemrxiv.fetch_for_keywords(
            keywords,
            exclude_keywords=exclude,
            max_per_keyword=limits.get("chemrxiv_per_keyword", 50),
            start_date=start_date,
        ):
            is_new = upsert_paper(conn, paper, fetched_at)
            if is_new:
                n_new_total += 1
            else:
                n_seen_total += 1

    # --- Europe PMC (bioRxiv 등) ---
    print("\n=== Europe PMC (bioRxiv/medRxiv) ===")
    with connect(db_path) as conn:
        for paper in europepmc.fetch_for_keywords(
            keywords,
            exclude_keywords=exclude,
            max_per_keyword=limits.get("europepmc_per_keyword", 100),
            start_date=start_date,
        ):
            is_new = upsert_paper(conn, paper, fetched_at)
            if is_new:
                n_new_total += 1
            else:
                n_seen_total += 1

    # state 파일 업데이트
    state_path = Path(cfg["state_file"])
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "last_backfill_at": fetched_at,
        "last_fetch_at": fetched_at,
    }
    state_path.write_text(json.dumps(state, indent=2))

    print(f"\n결과: 신규 {n_new_total}건, 기존(키워드만 머지) {n_seen_total}건")
    print(f"DB: {db_path}")
    print(f"다음 단계: Claude Code에서 /triage 실행")


if __name__ == "__main__":
    main()
