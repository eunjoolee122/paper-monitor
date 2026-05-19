"""Triage 점수를 DB에 저장.

사용:
    python scripts/save_scores.py < scores.json
또는:
    echo '[{"id":"arxiv:2401.12345","score":4,"reason":"..."}]' | python scripts/save_scores.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import update_score


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        print("stdin이 비어있음", file=sys.stderr)
        sys.exit(1)

    items = json.loads(raw)
    cfg = load_config()
    triaged_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    n = 0
    for it in items:
        update_score(
            cfg["db_path"],
            paper_id=it["id"],
            score=int(it["score"]),
            reason=it.get("reason", ""),
            triaged_at=triaged_at,
        )
        n += 1
    print(f"{n}건 점수 저장됨")


if __name__ == "__main__":
    main()
