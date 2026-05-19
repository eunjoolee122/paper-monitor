"""요약 markdown을 Obsidian 폴더에 저장하고 DB에 노트 경로 기록.

사용:
    python scripts/save_note.py --id arxiv:2401.12345 --file /tmp/note.md
또는 stdin으로 본문 전달:
    cat note.md | python scripts/save_note.py --id arxiv:2401.12345
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import get_paper, mark_summarized


def sanitize_filename(s: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\s\-\.]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:max_len]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--file", help="노트 본문 파일 경로 (없으면 stdin)")
    args = ap.parse_args()

    cfg = load_config()
    paper = get_paper(cfg["db_path"], args.id)
    if not paper:
        print(f"ID {args.id} 없음", file=sys.stderr)
        sys.exit(1)

    if args.file:
        content = Path(args.file).read_text()
    else:
        content = sys.stdin.read()

    notes_dir = Path(cfg["obsidian_notes_dir"]).expanduser()
    notes_dir.mkdir(parents=True, exist_ok=True)

    # 파일명: YYYY-MM-DD_<id>_<title-slug>.md
    safe_id = args.id.replace(":", "_").replace("/", "_")
    title_slug = sanitize_filename(paper["title"], max_len=60)
    filename = f"{paper['published_date']}_{safe_id}_{title_slug}.md"
    out_path = notes_dir / filename
    out_path.write_text(content)

    summarized_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    mark_summarized(
        cfg["db_path"],
        paper_id=args.id,
        note_path=str(out_path),
        summarized_at=summarized_at,
    )
    print(f"저장: {out_path}")


if __name__ == "__main__":
    main()
