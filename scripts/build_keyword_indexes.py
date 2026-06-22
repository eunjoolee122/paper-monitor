"""한글 요약된 논문을 keyword 그룹별로 묶어 Obsidian markdown 인덱스 생성.

queries.yaml의 core_keywords는 fetch 재현율을 위해 동의어를 넓게 잡아두기 때문에
(예: molecule generation / molecular generation / ligand generation …) 그대로
인덱스를 만들면 같은 맥락이 수십 개 페이지로 쪼개진다. 그래서 여기서 동의어를
대표 그룹으로 묶어 보여준다. DB(matched_keywords)는 손대지 않는다.

사용:
    python scripts/build_keyword_indexes.py [--min-score 3] [--outdir notes/by-keyword]

생성물:
    <obsidian_notes_dir>/by-keyword/_index.md          (전체 그룹 목차)
    <obsidian_notes_dir>/by-keyword/<group-slug>.md    (그룹별 논문 리스트)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_monitor.config import load_config
from paper_monitor.db import connect


# 동의어 → 대표 그룹. 인덱스 표시 단위. 순서가 곧 목차 순서.
KEYWORD_GROUPS: list[dict] = [
    {
        "name": "분자 생성",
        "slug": "molecule-generation",
        "keywords": [
            "molecular generation", "molecule generation", "generating molecules",
            "generation of molecules", "small molecule generation", "compound generation",
            "drug generation", "ligand generation", "ligand design", "molecule design",
            "molecular generative model", "3D molecule generation", "generative chemistry",
            "de novo molecular design", "de novo drug design",
        ],
    },
    {
        "name": "구조기반 설계",
        "slug": "structure-based-design",
        "keywords": [
            "structure-based drug design", "structure-based generative",
            "pocket-conditioned generation", "target-aware molecule generation",
        ],
    },
    {
        "name": "스캐폴드·프래그먼트",
        "slug": "scaffold-fragment",
        "keywords": [
            "scaffold hopping", "scaffold-constrained generation", "linker design",
            "fragment-based drug design", "PROTAC design",
        ],
    },
    {
        "name": "리드 최적화",
        "slug": "lead-optimization",
        "keywords": [
            "lead optimization", "molecular optimization", "molecule optimization",
            "molecular property optimization", "multi-parameter optimization molecule",
            "bioisosteric replacement", "matched molecular pairs", "free energy perturbation",
            "selectivity optimization", "Bayesian optimization molecule",
            "active learning chemistry",
        ],
    },
    {
        "name": "예측",
        "slug": "prediction",
        "keywords": [
            "binding affinity prediction", "ADMET prediction", "molecular property prediction",
            "drug-target interaction", "molecular docking deep learning",
        ],
    },
    {
        "name": "합성·표현",
        "slug": "synthesis-representation",
        "keywords": [
            "synthesizability", "retrosynthesis prediction", "molecular representation learning",
        ],
    },
]

OTHER_GROUP = {"name": "기타", "slug": "other", "keywords": []}

# lowercased keyword -> group slug
_KW_TO_SLUG: dict[str, str] = {}
for _g in KEYWORD_GROUPS:
    for _kw in _g["keywords"]:
        _KW_TO_SLUG[_kw.lower()] = _g["slug"]

_GROUP_BY_SLUG: dict[str, dict] = {g["slug"]: g for g in KEYWORD_GROUPS}
_GROUP_BY_SLUG[OTHER_GROUP["slug"]] = OTHER_GROUP


def slug_for_keyword(kw: str) -> str:
    """매칭된 raw 키워드를 그룹 slug로. 미정의면 'other'."""
    return _KW_TO_SLUG.get(kw.lower(), OTHER_GROUP["slug"])


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


def fetch_summarized(db_path: str, min_score: int) -> list[dict]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, title, abstract, published_date, score, score_reason,
                   matched_keywords, kr_summary, landing_url, pdf_url, source
            FROM papers
            WHERE score >= ? AND kr_summary IS NOT NULL AND status != 'skipped'
            ORDER BY score DESC, published_date DESC
            """,
            (min_score,),
        ).fetchall()
    return [dict(r) for r in rows]


SCORE_HEADER = {
    5: "## ⭐⭐⭐⭐⭐ 5점 — 핵심",
    4: "## ⭐⭐⭐⭐ 4점 — 본문 읽을 가치",
    3: "## ⭐⭐⭐ 3점 — 훑어볼 만함",
}


def render_group_page(group: dict, papers: list[dict], generated_at: str) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append(f'group: "{group["name"]}"')
    lines.append(f"papers_count: {len(papers)}")
    lines.append(f"generated_at: {generated_at}")
    lines.append("tags: [paper-index, drug-discovery]")
    lines.append("---")
    lines.append("")
    lines.append(f"# 🔍 {group['name']}")
    lines.append("")
    lines.append(f"총 **{len(papers)}편** (score ≥ 임계값, 발행일 내림차순)")
    lines.append("")

    by_score: dict[int, list[dict]] = defaultdict(list)
    for p in papers:
        by_score[int(p["score"] or 0)].append(p)

    for score in sorted(by_score.keys(), reverse=True):
        lines.append(SCORE_HEADER.get(score, f"## {score}점"))
        lines.append("")
        for p in by_score[score]:
            landing = p.get("landing_url") or ""
            title = (p["title"] or "").replace("[", "(").replace("]", ")")
            heading = f"### [{title}]({landing})" if landing else f"### {title}"
            lines.append(heading)
            lines.append(f"*{p['published_date']} · `{p['id']}`*")
            lines.append("")
            lines.append(p["kr_summary"] or "_(요약 없음)_")
            lines.append("")

            matched = json.loads(p.get("matched_keywords") or "[]")
            # 다른 그룹에도 매칭된 경우만 교차참조로 표기
            cross = [k for k in matched if slug_for_keyword(k) != group["slug"]]
            meta_parts = []
            if cross:
                meta_parts.append("매칭: " + ", ".join(f"`{k}`" for k in cross))
            if p.get("score_reason"):
                meta_parts.append(f"triage: {p['score_reason']}")
            if p.get("pdf_url"):
                meta_parts.append(f"[PDF]({p['pdf_url']})")
            if meta_parts:
                lines.append("> " + " · ".join(meta_parts))
                lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_top_index(by_slug: dict[str, list[dict]], generated_at: str) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append('title: "Paper Index by Keyword Group"')
    lines.append(f"generated_at: {generated_at}")
    lines.append("tags: [paper-index, drug-discovery]")
    lines.append("---")
    lines.append("")
    lines.append("# 📚 Paper Index — 키워드 그룹별")
    lines.append("")
    lines.append("score 임계값을 통과한 논문을 키워드 그룹별로 묶은 인덱스입니다.")
    lines.append("")

    # 정의된 그룹 순서대로, 마지막에 기타
    for group in [*KEYWORD_GROUPS, OTHER_GROUP]:
        items = by_slug.get(group["slug"])
        if not items:
            continue
        lines.append(f"- [[{group['slug']}|{group['name']}]] — {len(items)}편")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=int, default=None,
                    help="기본은 config.yaml의 summarize_threshold")
    ap.add_argument("--outdir", type=str, default=None,
                    help="기본은 <obsidian_notes_dir>/by-keyword")
    args = ap.parse_args()

    cfg = load_config()

    min_score = args.min_score if args.min_score is not None else cfg.get("summarize_threshold", 3)
    notes_root = Path(cfg["obsidian_notes_dir"]).expanduser()
    outdir = Path(args.outdir) if args.outdir else notes_root / "by-keyword"
    outdir.mkdir(parents=True, exist_ok=True)

    papers = fetch_summarized(cfg["db_path"], min_score)
    if not papers:
        print(f"한글 요약된 score>={min_score} 논문이 없음. 먼저 /kr-summarize 실행 필요.")
        return

    # 그룹별 그룹핑 (한 논문이 여러 그룹에 매칭되면 모두 등장, 그룹 내 중복 제거)
    by_slug: dict[str, list[dict]] = defaultdict(list)
    for p in papers:
        slugs = {slug_for_keyword(kw) for kw in json.loads(p.get("matched_keywords") or "[]")}
        if not slugs:
            slugs = {OTHER_GROUP["slug"]}
        for s in slugs:
            by_slug[s].append(p)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 그룹별 페이지
    written: list[Path] = []
    for group in [*KEYWORD_GROUPS, OTHER_GROUP]:
        items = by_slug.get(group["slug"])
        if not items:
            continue
        out_path = outdir / f"{group['slug']}.md"
        out_path.write_text(render_group_page(group, items, generated_at), encoding="utf-8")
        written.append(out_path)

    # 상위 인덱스
    top_path = outdir / "_index.md"
    top_path.write_text(render_top_index(by_slug, generated_at), encoding="utf-8")
    written.append(top_path)

    used = set(by_slug.keys())
    empty = [g["name"] for g in KEYWORD_GROUPS if g["slug"] not in used]

    print(f"생성 완료: {len(written)} 파일")
    print(f"  위치: {outdir}")
    print(f"  요약된 논문: {len(papers)}편 (score>={min_score})")
    print(f"  그룹: {len([g for g in [*KEYWORD_GROUPS, OTHER_GROUP] if by_slug.get(g['slug'])])}개")
    for group in [*KEYWORD_GROUPS, OTHER_GROUP]:
        n = len(by_slug.get(group["slug"], []))
        if n:
            print(f"    - {group['name']}: {n}편")
    if empty:
        print(f"  논문 없는 그룹: {', '.join(empty)}")
    print(f"  상위 인덱스: {top_path}")


if __name__ == "__main__":
    main()
