"""SQLite 기반 논문 메타데이터 저장소."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id              TEXT PRIMARY KEY,          -- 원본 ID (arxiv ID, DOI, chemrxiv ID 등)
    source          TEXT NOT NULL,             -- 'arxiv' | 'chemrxiv' | 'biorxiv' | 'pubmed'
    title           TEXT NOT NULL,
    authors         TEXT NOT NULL,             -- JSON list[str]
    abstract        TEXT,
    published_date  TEXT NOT NULL,             -- ISO date
    pdf_url         TEXT,
    landing_url     TEXT,
    categories      TEXT,                      -- JSON list[str]
    fetched_at      TEXT NOT NULL,             -- ISO timestamp
    matched_keywords TEXT,                     -- JSON list[str] (어떤 키워드에서 매칭됐는지)

    -- triage 결과
    score           INTEGER,                   -- 0~5, NULL이면 triage 안 됨
    score_reason    TEXT,
    triaged_at      TEXT,

    -- summarize 결과
    note_path       TEXT,                      -- Obsidian note 상대경로
    summarized_at   TEXT,

    -- 워크플로우
    status          TEXT NOT NULL DEFAULT 'new'  -- 'new' | 'triaged' | 'summarized' | 'skipped'
);

CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_date);
CREATE INDEX IF NOT EXISTS idx_papers_score ON papers(score);

CREATE TABLE IF NOT EXISTS fetch_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    source      TEXT NOT NULL,
    keyword     TEXT,
    n_new       INTEGER DEFAULT 0,
    n_seen      INTEGER DEFAULT 0,
    note        TEXT
);
"""


@dataclass
class Paper:
    id: str
    source: str
    title: str
    authors: list[str]
    abstract: str
    published_date: str
    pdf_url: Optional[str] = None
    landing_url: Optional[str] = None
    categories: Optional[list[str]] = None
    matched_keywords: Optional[list[str]] = None


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def upsert_paper(conn: sqlite3.Connection, p: Paper, fetched_at: str) -> bool:
    """새 논문이면 True, 이미 있으면 False (matched_keywords만 머지)."""
    cur = conn.execute("SELECT matched_keywords FROM papers WHERE id = ?", (p.id,))
    row = cur.fetchone()
    if row is not None:
        # 이미 있는 논문 - 키워드 머지만 함
        existing = set(json.loads(row["matched_keywords"] or "[]"))
        new_keywords = set(p.matched_keywords or [])
        merged = sorted(existing | new_keywords)
        conn.execute(
            "UPDATE papers SET matched_keywords = ? WHERE id = ?",
            (json.dumps(merged), p.id),
        )
        return False

    conn.execute(
        """
        INSERT INTO papers (
            id, source, title, authors, abstract, published_date,
            pdf_url, landing_url, categories, fetched_at, matched_keywords, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
        """,
        (
            p.id,
            p.source,
            p.title,
            json.dumps(p.authors),
            p.abstract,
            p.published_date,
            p.pdf_url,
            p.landing_url,
            json.dumps(p.categories or []),
            fetched_at,
            json.dumps(p.matched_keywords or []),
        ),
    )
    return True


def list_papers(
    db_path: str | Path,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 50,
) -> list[dict]:
    q = "SELECT * FROM papers WHERE 1=1"
    args: list = []
    if status is not None:
        q += " AND status = ?"
        args.append(status)
    if min_score is not None:
        q += " AND score >= ?"
        args.append(min_score)
    q += " ORDER BY published_date DESC LIMIT ?"
    args.append(limit)
    with connect(db_path) as conn:
        rows = conn.execute(q, args).fetchall()
    return [dict(r) for r in rows]


def get_paper(db_path: str | Path, paper_id: str) -> Optional[dict]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    return dict(row) if row else None


def update_score(
    db_path: str | Path,
    paper_id: str,
    score: int,
    reason: str,
    triaged_at: str,
) -> None:
    new_status = "triaged" if score > 0 else "skipped"
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE papers
            SET score = ?, score_reason = ?, triaged_at = ?, status = ?
            WHERE id = ?
            """,
            (score, reason, triaged_at, new_status, paper_id),
        )


def mark_summarized(
    db_path: str | Path, paper_id: str, note_path: str, summarized_at: str
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE papers
            SET note_path = ?, summarized_at = ?, status = 'summarized'
            WHERE id = ?
            """,
            (note_path, summarized_at, paper_id),
        )


def stats(db_path: str | Path) -> dict:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM papers GROUP BY status"
        ).fetchall()
        score_rows = conn.execute(
            "SELECT score, COUNT(*) AS n FROM papers WHERE score IS NOT NULL GROUP BY score"
        ).fetchall()
    return {
        "by_status": {r["status"]: r["n"] for r in rows},
        "by_score": {r["score"]: r["n"] for r in score_rows},
    }
