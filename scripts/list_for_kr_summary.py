"""한글 요약 대기 중인 논문(score>=N AND kr_summary IS NULL) JSON 출력.

Claude Code 슬래시 커맨드(/kr-summarize)에서 호출.

사용:
    python scripts/list_for_kr_summary.py [--limit 20] [--min-score 3]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import connect


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--min-score", type=int, default=None,
                    help="기본은 config.yaml의 summarize_threshold")
    args = ap.parse_args()

    cfg = load_config()
    threshold = args.min_score if args.min_score is not None else cfg.get("summarize_threshold", 3)

    with connect(cfg["db_path"]) as conn:
        rows = conn.execute(
            """
            SELECT id, title, abstract, published_date, score, matched_keywords
            FROM papers
            WHERE score >= ? AND kr_summary IS NULL AND status != 'skipped'
            ORDER BY score DESC, published_date DESC
            LIMIT ?
            """,
            (threshold, args.limit),
        ).fetchall()

    out = [
        {
            "id": r["id"],
            "title": r["title"],
            "abstract": r["abstract"],
            "published_date": r["published_date"],
            "score": r["score"],
            "matched_keywords": json.loads(r["matched_keywords"] or "[]"),
        }
        for r in rows
    ]
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
