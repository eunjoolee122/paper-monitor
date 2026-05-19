"""Triage 대기 중인 논문(status='new')을 JSON으로 출력.

Claude Code 슬래시 커맨드에서 이걸 호출해서 abstract들 받아옴.

사용:
    python scripts/list_untriaged.py [--limit 20]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import list_papers


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    cfg = load_config()
    papers = list_papers(cfg["db_path"], status="new", limit=args.limit)

    # triage에 필요한 필드만 슬림하게 출력
    slim = [
        {
            "id": p["id"],
            "source": p["source"],
            "title": p["title"],
            "abstract": p["abstract"],
            "published_date": p["published_date"],
            "matched_keywords": json.loads(p["matched_keywords"] or "[]"),
        }
        for p in papers
    ]
    print(json.dumps(slim, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
