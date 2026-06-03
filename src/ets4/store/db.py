from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ets4.identity import canonicalize_url, normalize_title, title_similarity

SCHEMA_VERSION = 3


def connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS run_manifests (
            run_id TEXT PRIMARY KEY,
            issue_id TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source_snapshot_id TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            model_policy_json TEXT NOT NULL,
            cost_budget_json TEXT NOT NULL,
            paper_budget_json TEXT NOT NULL,
            allowed_actions_json TEXT NOT NULL,
            force_include_json TEXT NOT NULL,
            force_exclude_json TEXT NOT NULL,
            automation_mode TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            url TEXT NOT NULL,
            domain TEXT NOT NULL,
            priority TEXT NOT NULL,
            lookback_days INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS source_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL REFERENCES sources(id),
            run_id TEXT REFERENCES run_manifests(run_id),
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            message TEXT,
            candidate_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            canonical_url TEXT NOT NULL,
            abstract TEXT NOT NULL DEFAULT '',
            authors TEXT NOT NULL DEFAULT '',
            source_id TEXT REFERENCES sources(id),
            published_date TEXT,
            doi TEXT,
            arxiv_id TEXT,
            normalized_title TEXT NOT NULL DEFAULT '',
            duplicate_of_paper_id TEXT REFERENCES papers(id),
            status TEXT NOT NULL DEFAULT 'candidate',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_canonical_url
        ON papers(canonical_url);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_doi
        ON papers(doi)
        WHERE doi IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_arxiv_id
        ON papers(arxiv_id)
        WHERE arxiv_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_papers_normalized_title
        ON papers(normalized_title);

        CREATE TABLE IF NOT EXISTS triage_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL REFERENCES papers(id),
            run_id TEXT NOT NULL REFERENCES run_manifests(run_id),
            provider TEXT NOT NULL,
            decision TEXT NOT NULL,
            category_hint TEXT NOT NULL,
            forecasting_signal TEXT NOT NULL,
            economic_signal TEXT NOT NULL,
            score REAL NOT NULL,
            confidence REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(paper_id, run_id)
        );

        CREATE TABLE IF NOT EXISTS candidate_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL REFERENCES run_manifests(run_id),
            paper_id TEXT NOT NULL REFERENCES papers(id),
            selection_stage TEXT NOT NULL,
            rank INTEGER NOT NULL,
            selection_score REAL NOT NULL,
            forced INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL,
            selected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(run_id, paper_id, selection_stage),
            UNIQUE(run_id, selection_stage, rank)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            paper_id TEXT NOT NULL REFERENCES papers(id),
            run_id TEXT REFERENCES run_manifests(run_id),
            source_uri TEXT NOT NULL,
            content_type TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            page_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash
        ON documents(paper_id, content_sha256);

        CREATE TABLE IF NOT EXISTS document_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL REFERENCES documents(id),
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(document_id, page_number)
        );

        CREATE TABLE IF NOT EXISTS evidence_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL REFERENCES papers(id),
            document_id TEXT NOT NULL REFERENCES documents(id),
            page_number INTEGER NOT NULL,
            kind TEXT NOT NULL,
            label TEXT NOT NULL,
            text TEXT NOT NULL,
            source_locator TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS document_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT REFERENCES papers(id),
            document_id TEXT REFERENCES documents(id),
            run_id TEXT REFERENCES run_manifests(run_id),
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    _ensure_column(conn, "papers", "normalized_title", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "papers", "duplicate_of_paper_id", "TEXT REFERENCES papers(id)")
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, declaration: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def insert_manifest(conn: sqlite3.Connection, manifest: Any) -> None:
    data = manifest.to_dict()
    conn.execute(
        """
        INSERT OR REPLACE INTO run_manifests (
            run_id, issue_id, issue_date, created_at, source_snapshot_id,
            prompt_version, model_policy_json, cost_budget_json, paper_budget_json,
            allowed_actions_json, force_include_json, force_exclude_json, automation_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["run_id"],
            data["issue_id"],
            data["issue_date"],
            data["created_at"],
            data["source_snapshot_id"],
            data["prompt_version"],
            json.dumps(data["model_policy"], sort_keys=True),
            json.dumps(data["cost_budget"], sort_keys=True),
            json.dumps(data["paper_budget"], sort_keys=True),
            json.dumps(data["allowed_actions"]),
            json.dumps(data["force_include"]),
            json.dumps(data["force_exclude"]),
            data["automation_mode"],
        ),
    )
    conn.commit()


def run_exists(conn: sqlite3.Connection, run_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM run_manifests WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    return row is not None


def upsert_source(conn: sqlite3.Connection, source: Any) -> None:
    conn.execute(
        """
        INSERT INTO sources (id, name, type, url, domain, priority, lookback_days)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            url = excluded.url,
            domain = excluded.domain,
            priority = excluded.priority,
            lookback_days = excluded.lookback_days,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            source.id,
            source.name,
            source.type,
            source.url,
            source.domain,
            source.priority,
            source.lookback_days,
        ),
    )


def upsert_paper(
    conn: sqlite3.Connection,
    *,
    paper_id: str,
    title: str,
    canonical_url: str,
    abstract: str = "",
    authors: str = "",
    source_id: str | None = None,
    published_date: str | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
    duplicate_similarity_threshold: float = 0.96,
) -> str:
    canonical_url = canonicalize_url(canonical_url)
    doi = doi.lower() if doi else None
    arxiv_id = arxiv_id.strip() if arxiv_id else None
    normalized_title = normalize_title(title)
    existing_id = find_duplicate_paper_id(
        conn,
        title=title,
        canonical_url=canonical_url,
        doi=doi,
        arxiv_id=arxiv_id,
        similarity_threshold=duplicate_similarity_threshold,
    )
    resolved_id = existing_id or paper_id
    duplicate_of = existing_id if existing_id and existing_id != paper_id else None
    conn.execute(
        """
        INSERT INTO papers (
            id, title, canonical_url, abstract, authors, source_id,
            published_date, doi, arxiv_id, normalized_title, duplicate_of_paper_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            abstract = COALESCE(NULLIF(excluded.abstract, ''), papers.abstract),
            authors = COALESCE(NULLIF(excluded.authors, ''), papers.authors),
            source_id = COALESCE(excluded.source_id, papers.source_id),
            published_date = COALESCE(excluded.published_date, papers.published_date),
            doi = COALESCE(excluded.doi, papers.doi),
            arxiv_id = COALESCE(excluded.arxiv_id, papers.arxiv_id),
            normalized_title = COALESCE(NULLIF(excluded.normalized_title, ''), papers.normalized_title),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            resolved_id,
            title,
            canonical_url,
            abstract,
            authors,
            source_id,
            published_date,
            doi,
            arxiv_id,
            normalized_title,
            duplicate_of,
        ),
    )
    return resolved_id


def find_duplicate_paper_id(
    conn: sqlite3.Connection,
    *,
    title: str,
    canonical_url: str,
    doi: str | None,
    arxiv_id: str | None,
    similarity_threshold: float,
) -> str | None:
    canonical_url = canonicalize_url(canonical_url)
    checks = [
        ("canonical_url", canonical_url),
        ("doi", doi),
        ("arxiv_id", arxiv_id),
    ]
    for column, value in checks:
        if not value:
            continue
        row = conn.execute(f"SELECT id FROM papers WHERE {column} = ? LIMIT 1", (value,)).fetchone()
        if row:
            return str(row["id"])

    normalized = normalize_title(title)
    if not normalized:
        return None
    row = conn.execute(
        "SELECT id FROM papers WHERE normalized_title = ? LIMIT 1",
        (normalized,),
    ).fetchone()
    if row:
        return str(row["id"])

    for candidate in conn.execute("SELECT id, title FROM papers").fetchall():
        if title_similarity(title, candidate["title"]) >= similarity_threshold:
            return str(candidate["id"])
    return None


def insert_source_event(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    run_id: str,
    status: str,
    message: str,
    candidate_count: int = 0,
) -> None:
    _ensure_column(conn, "source_events", "candidate_count", "INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """
        INSERT INTO source_events(source_id, run_id, status, message, candidate_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (source_id, run_id, status, message, candidate_count),
    )


def insert_document(
    conn: sqlite3.Connection,
    *,
    document_id: str,
    paper_id: str,
    run_id: str | None,
    source_uri: str,
    content_type: str,
    content_sha256: str,
    page_count: int,
    status: str,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO documents (
            id, paper_id, run_id, source_uri, content_type, content_sha256,
            page_count, status, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            run_id = excluded.run_id,
            source_uri = excluded.source_uri,
            content_type = excluded.content_type,
            content_sha256 = excluded.content_sha256,
            page_count = excluded.page_count,
            status = excluded.status,
            error_message = excluded.error_message,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            document_id,
            paper_id,
            run_id,
            source_uri,
            content_type,
            content_sha256,
            page_count,
            status,
            error_message,
        ),
    )


def insert_document_page(
    conn: sqlite3.Connection,
    *,
    document_id: str,
    page_number: int,
    text: str,
) -> None:
    conn.execute(
        """
        INSERT INTO document_pages (document_id, page_number, text, char_count)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(document_id, page_number) DO UPDATE SET
            text = excluded.text,
            char_count = excluded.char_count
        """,
        (document_id, page_number, text, len(text)),
    )


def insert_evidence_item(
    conn: sqlite3.Connection,
    *,
    paper_id: str,
    document_id: str,
    page_number: int,
    kind: str,
    label: str,
    text: str,
    source_locator: str,
    confidence: float = 1.0,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_items (
            paper_id, document_id, page_number, kind, label, text, source_locator, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (paper_id, document_id, page_number, kind, label, text, source_locator, confidence),
    )


def insert_document_event(
    conn: sqlite3.Connection,
    *,
    paper_id: str | None,
    document_id: str | None,
    run_id: str | None,
    status: str,
    message: str,
) -> None:
    conn.execute(
        """
        INSERT INTO document_events (paper_id, document_id, run_id, status, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (paper_id, document_id, run_id, status, message),
    )
