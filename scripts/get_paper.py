"""특정 논문 한 건 또는 요약 대기 중인 상위 N건 메타데이터 조회.

사용:
    python scripts/get_paper.py --id arxiv:2401.12345
    python scripts/get_paper.py --next 5      # 요약 대상 상위 5건
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import get_paper, list_papers


def serialize(row: dict) -> dict:
    return {
        "id": row["id"],
        "source": row["source"],
        "title": row["title"],
        "authors": json.loads(row["authors"] or "[]"),
        "abstract": row["abstract"],
        "published_date": row["published_date"],
        "pdf_url": row["pdf_url"],
        "landing_url": row["landing_url"],
        "categories": json.loads(row["categories"] or "[]"),
        "matched_keywords": json.loads(row["matched_keywords"] or "[]"),
        "score": row["score"],
        "score_reason": row["score_reason"],
        "status": row["status"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=str)
    ap.add_argument("--next", type=int, help="요약 대기중 상위 N건 (status=triaged, score 높은 순)")
    args = ap.parse_args()

    cfg = load_config()

    if args.id:
        row = get_paper(cfg["db_path"], args.id)
        if not row:
            print(f"ID {args.id} 없음", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(serialize(row), indent=2, ensure_ascii=False))
    elif args.next:
        threshold = cfg.get("summarize_threshold", 3)
        rows = list_papers(
            cfg["db_path"],
            status="triaged",
            min_score=threshold,
            limit=args.next,
        )
        # score DESC로 다시 정렬
        rows.sort(key=lambda r: (r["score"] or 0), reverse=True)
        out = [serialize(r) for r in rows]
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
