"""arXiv Kaggle dump을 읽어 메타데이터를 DB로 import.

대규모 백필 전용. arxiv.org API를 전혀 호출하지 않으므로 429 위험 없음.
- Dataset: Cornell-University/arxiv (Kaggle, 월 단위 업데이트, ~4GB JSON Lines)
- queries.yaml의 keywords/categories/exclude_keywords/date_range로 필터링 후 upsert

사용:
    # 1) 최초 1회: Kaggle 인증 필요 (~/.kaggle/kaggle.json 또는 환경변수)
    # 2) 실행:
    python scripts/import_arxiv_dump.py

이후 새 논문은 scripts/fetch_new.py (incremental)로 계속 받는다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import kagglehub
from tqdm import tqdm

from paper_monitor.config import load_config, load_queries
from paper_monitor.db import Paper, connect, init_db, upsert_paper
from paper_monitor.fetchers.base import contains_any, should_exclude


KAGGLE_DATASET = "Cornell-University/arxiv"
DUMP_FILENAME = "arxiv-metadata-oai-snapshot.json"
COMMIT_EVERY = 5000   # N건마다 commit해서 중간 중단 대비


def _parse_v1_date(versions: list[dict]) -> str | None:
    """versions[0].created ("Mon, 2 Apr 2007 19:18:42 GMT") -> "YYYY-MM-DD"."""
    if not versions:
        return None
    created = versions[0].get("created")
    if not created:
        return None
    try:
        dt = datetime.strptime(created, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        return None
    return dt.date().isoformat()


def _authors_from_record(rec: dict) -> list[str]:
    parsed = rec.get("authors_parsed") or []
    out: list[str] = []
    for parts in parsed:
        last = parts[0] if len(parts) > 0 else ""
        first = parts[1] if len(parts) > 1 else ""
        suffix = parts[2] if len(parts) > 2 else ""
        name = " ".join(s for s in (first, last, suffix) if s).strip()
        if name:
            out.append(name)
    if out:
        return out
    raw = rec.get("authors") or ""
    return [a.strip() for a in raw.split(",") if a.strip()]


def iter_dump(dump_path: Path) -> Iterator[dict]:
    with open(dump_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def filter_record(
    rec: dict,
    *,
    cat_set: set[str],
    keywords: list[str],
    exclude: list[str],
    start_date: str | None,
    end_date: str | None,
) -> Paper | None:
    """매치하면 Paper 반환, 아니면 None. 가벼운 필터부터 순차 적용."""
    rec_cats = (rec.get("categories") or "").split()
    if cat_set and not (cat_set & set(rec_cats)):
        return None

    published = _parse_v1_date(rec.get("versions") or [])
    if published is None:
        return None
    if start_date and published < start_date:
        return None
    if end_date and published > end_date:
        return None

    title = (rec.get("title") or "").replace("\n", " ").strip()
    abstract = (rec.get("abstract") or "").replace("\n", " ").strip()
    blob = f"{title} {abstract}"

    if should_exclude(blob, exclude):
        return None

    matched = contains_any(blob, keywords)
    if not matched:
        return None

    arxiv_id = (rec.get("id") or "").strip()
    if not arxiv_id:
        return None

    return Paper(
        id=f"arxiv:{arxiv_id}",
        source="arxiv",
        title=title,
        authors=_authors_from_record(rec),
        abstract=abstract,
        published_date=published,
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        landing_url=f"https://arxiv.org/abs/{arxiv_id}",
        categories=rec_cats,
        matched_keywords=matched,
    )


def _resolve_dump_path() -> Path:
    print(f"Downloading Kaggle dataset (cached after first run) ...")
    dataset_dir = Path(kagglehub.dataset_download(KAGGLE_DATASET))
    target = dataset_dir / DUMP_FILENAME
    if target.exists():
        return target
    # 파일명이 달라질 수 있으니 폴더 안 첫 JSON으로 fallback
    candidates = sorted(dataset_dir.glob("*.json"))
    if not candidates:
        raise FileNotFoundError(f"No JSON file found under {dataset_dir}")
    return candidates[0]


def main() -> None:
    cfg = load_config()
    q = load_queries()
    db_path = cfg["db_path"]
    init_db(db_path)

    keywords = q["core_keywords"]
    exclude = q.get("exclude_keywords", [])
    cat_set = set(q.get("arxiv_categories") or [])
    date_range = q.get("date_range") or {}
    start_date = date_range.get("start")
    end_date = date_range.get("end")

    print("=== arXiv Kaggle dump import ===")
    print(f"  categories : {sorted(cat_set) or '(any)'}")
    print(f"  date range : {start_date or '(none)'} ~ {end_date or 'today'}")
    print(f"  keywords   : {len(keywords)}, exclude: {len(exclude)}")
    print()

    dump_path = _resolve_dump_path()
    size_mb = dump_path.stat().st_size / (1024 * 1024)
    print(f"  dump: {dump_path}")
    print(f"  size: {size_mb:,.1f} MB")
    print()

    fetched_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    n_total = n_matched = n_new = n_seen = 0
    n_since_commit = 0

    with connect(db_path) as conn:
        for rec in tqdm(iter_dump(dump_path), unit="rec", unit_scale=True):
            n_total += 1
            paper = filter_record(
                rec,
                cat_set=cat_set,
                keywords=keywords,
                exclude=exclude,
                start_date=start_date,
                end_date=end_date,
            )
            if paper is None:
                continue
            n_matched += 1
            if upsert_paper(conn, paper, fetched_at):
                n_new += 1
            else:
                n_seen += 1
            n_since_commit += 1
            if n_since_commit >= COMMIT_EVERY:
                conn.commit()
                n_since_commit = 0

    # state 파일 머지
    state_path = Path(cfg["state_file"])
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state: dict = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            state = {}
    state["last_arxiv_dump_import_at"] = fetched_at
    state.setdefault("last_backfill_at", fetched_at)
    state_path.write_text(json.dumps(state, indent=2))

    print()
    print("=== 결과 ===")
    print(f"  처리한 줄 수 : {n_total:,}")
    print(f"  필터 통과    : {n_matched:,}")
    print(f"  신규 insert : {n_new:,}")
    print(f"  기존 (merge): {n_seen:,}")
    print()
    print(f"DB: {db_path}")
    print("다음 단계:")
    print("  - chemRxiv/Europe PMC 백필: python scripts/backfill.py")
    print("    (arxiv 부분은 이제 dump가 대신하니까 limits.arxiv_per_keyword를")
    print("     0으로 두거나 backfill.py의 arxiv 블록을 스킵해도 됨)")
    print("  - 이후 신규 논문: python scripts/fetch_new.py")


if __name__ == "__main__":
    main()
