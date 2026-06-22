"""한글 abstract 요약을 DB에 저장.

사용:
    python scripts/save_kr_summary.py < summaries.json
또는:
    echo '[{"id":"arxiv:2401.12345","kr_summary":"..."}]' | python scripts/save_kr_summary.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import save_kr_summary


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        print("stdin이 비어있음", file=sys.stderr)
        sys.exit(1)

    items = json.loads(raw)
    cfg = load_config()
    kr_summarized_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    n = 0
    for it in items:
        save_kr_summary(
            cfg["db_path"],
            paper_id=it["id"],
            kr_summary=it["kr_summary"].strip(),
            kr_summarized_at=kr_summarized_at,
        )
        n += 1
    print(f"{n}건 한글 요약 저장됨")


if __name__ == "__main__":
    main()
