"""증분 fetch: 마지막 실행 이후 추가된 논문만 가져옴.

cron / GitHub Actions에서 매일 또는 매주 실행.

사용:
    python scripts/fetch_new.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config, load_queries
from paper_monitor.db import connect, init_db, upsert_paper
from paper_monitor.fetchers import arxiv, chemrxiv, europepmc


def main() -> None:
    cfg = load_config()
    q = load_queries()

    db_path = cfg["db_path"]
    init_db(db_path)

    state_path = Path(cfg["state_file"])
    if state_path.exists():
        state = json.loads(state_path.read_text())
        last_fetch = state.get("last_fetch_at", "")[:10]
    else:
        # state 없으면 7일 전부터
        last_fetch = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        state = {}

    print(f"마지막 fetch: {last_fetch}, 그 이후 새 논문만 수집")

    keywords = q["core_keywords"]
    exclude = q.get("exclude_keywords", [])
    arxiv_cats = q.get("arxiv_categories")
    # 증분일 땐 키워드당 결과를 더 적게
    limits = q.get("limits", {})

    fetched_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    n_new = 0

    for name, fetcher_call in [
        (
            "arxiv",
            lambda: arxiv.fetch_for_keywords(
                keywords,
                categories=arxiv_cats,
                exclude_keywords=exclude,
                max_per_keyword=min(limits.get("arxiv_per_keyword", 100), 30),
                start_date=last_fetch,
            ),
        ),
        (
            "chemrxiv",
            lambda: chemrxiv.fetch_for_keywords(
                keywords,
                exclude_keywords=exclude,
                max_per_keyword=min(limits.get("chemrxiv_per_keyword", 50), 20),
                start_date=last_fetch,
            ),
        ),
        (
            "europepmc",
            lambda: europepmc.fetch_for_keywords(
                keywords,
                exclude_keywords=exclude,
                max_per_keyword=min(limits.get("europepmc_per_keyword", 100), 30),
                start_date=last_fetch,
            ),
        ),
    ]:
        print(f"\n=== {name} ===")
        with connect(db_path) as conn:
            for paper in fetcher_call():
                if upsert_paper(conn, paper, fetched_at):
                    n_new += 1

    state["last_fetch_at"] = fetched_at
    state_path.write_text(json.dumps(state, indent=2))
    print(f"\n신규 {n_new}건. 다음 단계: /triage")


if __name__ == "__main__":
    main()
