"""DB 통계 출력.

사용:
    python scripts/stats.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import stats


def main() -> None:
    cfg = load_config()
    s = stats(cfg["db_path"])
    print(json.dumps(s, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
