"""본문 노트(status='summarized')를 점수·그룹·발행일순으로 묶어 Obsidian 인덱스 생성.

claude_paper 폴더는 본문 노트 .md가 평평하게 쌓이기만 하므로, 이 스크립트가
그 노트들을 키워드 그룹별로 묶고 (그룹 내) 점수 내림차순 → 발행일 내림차순으로
정렬해 _index.md를 만든다. 각 항목은 해당 노트로 가는 Obsidian wikilink.

키워드→그룹 매핑은 build_keyword_indexes.py의 KEYWORD_GROUPS를 그대로 재사용.

사용:
    python scripts/build_paper_index.py [--outdir <claude_paper 폴더>]
기본 outdir 없으면 config의 obsidian_notes_dir 아래 claude_paper.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import connect
# 그룹 정의 재사용 (단일 소스)
from build_keyword_indexes import KEYWORD_GROUPS, OTHER_GROUP, slug_for_keyword


def fetch_summarized(db_path: str) -> list[dict]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, title, score, published_date, note_path,
                   matched_keywords, landing_url
            FROM papers
            WHERE status = 'summarized' AND note_path IS NOT NULL
            ORDER BY score DESC, published_date DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def stars(score: int) -> str:
    return "⭐" * int(score or 0)


def note_link(p: dict) -> str:
    """노트 파일명(확장자 제외)으로 wikilink. 노트가 없으면 landing_url로 폴백."""
    title = (p["title"] or "").replace("[", "(").replace("]", ")")
    note_path = p.get("note_path")
    if note_path:
        stem = Path(note_path).stem
        return f"[[{stem}|{title}]]"
    landing = p.get("landing_url") or ""
    return f"[{title}]({landing})" if landing else title


def render_index(by_slug: dict[str, list[dict]], total: int, generated_at: str) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append('title: "Paper Notes Index"')
    lines.append(f"papers_count: {total}")
    lines.append(f"generated_at: {generated_at}")
    lines.append("tags: [paper-index, drug-discovery, deep-notes]")
    lines.append("---")
    lines.append("")
    lines.append("# 📑 본문 노트 인덱스 (claude_paper)")
    lines.append("")
    lines.append(f"본문까지 정독한 노트 **{total}편**. 키워드 그룹별 → 점수 내림차순 → 발행일 내림차순.")
    lines.append("")

    for group in [*KEYWORD_GROUPS, OTHER_GROUP]:
        items = by_slug.get(group["slug"])
        if not items:
            continue
        lines.append(f"## {group['name']} ({len(items)}편)")
        lines.append("")
        for p in items:  # 이미 score desc, published desc 정렬됨
            lines.append(f"- {stars(p['score'])} {note_link(p)} — *{p['published_date']}* · `{p['id']}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=str, default=None,
                    help="기본은 <obsidian_notes_dir>/claude_paper")
    args = ap.parse_args()

    cfg = load_config()
    outdir = Path(args.outdir) if args.outdir \
        else Path(cfg["obsidian_notes_dir"]).expanduser() / "claude_paper"
    outdir.mkdir(parents=True, exist_ok=True)

    papers = fetch_summarized(cfg["db_path"])
    if not papers:
        print("본문 노트(status='summarized')가 없음. 먼저 /summarize 실행 필요.")
        return

    # 그룹별 그룹핑 (한 논문이 여러 그룹이면 모두 등장). 정렬은 fetch에서 이미 됨.
    by_slug: dict[str, list[dict]] = defaultdict(list)
    for p in papers:
        slugs = {slug_for_keyword(kw) for kw in json.loads(p.get("matched_keywords") or "[]")}
        if not slugs:
            slugs = {OTHER_GROUP["slug"]}
        for s in slugs:
            by_slug[s].append(p)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_path = outdir / "_index.md"
    out_path.write_text(render_index(by_slug, len(papers), generated_at), encoding="utf-8")

    print(f"생성 완료: {out_path}")
    print(f"  본문 노트: {len(papers)}편")
    for group in [*KEYWORD_GROUPS, OTHER_GROUP]:
        n = len(by_slug.get(group["slug"], []))
        if n:
            print(f"    - {group['name']}: {n}편")


if __name__ == "__main__":
    main()
