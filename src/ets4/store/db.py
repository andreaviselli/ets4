from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


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
            message TEXT
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
            status TEXT NOT NULL DEFAULT 'candidate',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_canonical_url
        ON papers(canonical_url);

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
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()


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
) -> None:
    conn.execute(
        """
        INSERT INTO papers (
            id, title, canonical_url, abstract, authors, source_id,
            published_date, doi, arxiv_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(canonical_url) DO UPDATE SET
            title = excluded.title,
            abstract = excluded.abstract,
            authors = excluded.authors,
            source_id = excluded.source_id,
            published_date = excluded.published_date,
            doi = excluded.doi,
            arxiv_id = excluded.arxiv_id,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            paper_id,
            title,
            canonical_url,
            abstract,
            authors,
            source_id,
            published_date,
            doi,
            arxiv_id,
        ),
    )
