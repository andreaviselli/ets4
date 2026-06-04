from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Any


class DossierBuildError(RuntimeError):
    """Raised when a paper cannot be reviewed because evidence is missing."""


@dataclass(frozen=True)
class EvidenceDossier:
    id: str
    paper_id: str
    run_id: str
    document_id: str
    evidence_count: int
    payload: dict[str, Any]


def build_evidence_dossier(
    conn: sqlite3.Connection,
    *,
    paper_id: str,
    run_id: str,
    max_evidence_items: int = 80,
) -> EvidenceDossier:
    paper = conn.execute(
        """
        SELECT id, title, canonical_url, abstract, authors, published_date, doi, arxiv_id
        FROM papers
        WHERE id = ?
        """,
        (paper_id,),
    ).fetchone()
    if not paper:
        raise DossierBuildError(f"Paper not found: {paper_id}")

    document = conn.execute(
        """
        SELECT id, source_uri, content_type, content_sha256, page_count, status
        FROM documents
        WHERE paper_id = ? AND status = 'ok'
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (paper_id,),
    ).fetchone()
    if not document:
        raise DossierBuildError(f"No successful extracted document for paper: {paper_id}")

    pages = conn.execute(
        """
        SELECT page_number, char_count
        FROM document_pages
        WHERE document_id = ?
        ORDER BY page_number ASC
        """,
        (document["id"],),
    ).fetchall()
    if not pages:
        raise DossierBuildError(f"No extracted pages for document: {document['id']}")

    evidence_rows = conn.execute(
        """
        SELECT id, kind, label, page_number, text, source_locator, confidence
        FROM evidence_items
        WHERE paper_id = ? AND document_id = ?
        ORDER BY page_number ASC, id ASC
        LIMIT ?
        """,
        (paper_id, document["id"], max_evidence_items),
    ).fetchall()
    if not evidence_rows:
        raise DossierBuildError(f"No evidence items for paper: {paper_id}")

    evidence_items = [
        {
            "id": int(row["id"]),
            "kind": row["kind"],
            "label": row["label"],
            "page_number": int(row["page_number"]),
            "text": row["text"],
            "source_locator": row["source_locator"],
            "confidence": float(row["confidence"]),
        }
        for row in evidence_rows
    ]
    evidence_by_kind: dict[str, int] = {}
    for item in evidence_items:
        evidence_by_kind[item["kind"]] = evidence_by_kind.get(item["kind"], 0) + 1

    dossier_id = _dossier_id(run_id=run_id, paper_id=paper_id)
    payload = {
        "dossier_id": dossier_id,
        "run_id": run_id,
        "paper": {
            "id": paper["id"],
            "title": paper["title"],
            "canonical_url": paper["canonical_url"],
            "abstract": paper["abstract"],
            "authors": paper["authors"],
            "published_date": paper["published_date"],
            "doi": paper["doi"],
            "arxiv_id": paper["arxiv_id"],
        },
        "document": {
            "id": document["id"],
            "source_uri": document["source_uri"],
            "content_type": document["content_type"],
            "content_sha256": document["content_sha256"],
            "page_count": int(document["page_count"]),
        },
        "pages": [
            {
                "page_number": int(row["page_number"]),
                "char_count": int(row["char_count"]),
            }
            for row in pages
        ],
        "evidence_count": len(evidence_items),
        "evidence_by_kind": evidence_by_kind,
        "evidence_items": evidence_items,
        "review_constraints": {
            "must_cite_evidence_item_ids": True,
            "must_flag_missing_evidence": True,
            "no_claims_without_evidence": True,
        },
    }
    return EvidenceDossier(
        id=dossier_id,
        paper_id=paper_id,
        run_id=run_id,
        document_id=document["id"],
        evidence_count=len(evidence_items),
        payload=payload,
    )


def _dossier_id(*, run_id: str, paper_id: str) -> str:
    digest = hashlib.sha256(f"{run_id}|{paper_id}".encode("utf-8")).hexdigest()
    return f"dossier-{digest[:16]}"
