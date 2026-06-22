from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import sqlite3

from ets4.store.db import (
    insert_document,
    insert_document_event,
    insert_document_page,
    insert_evidence_item,
)

from .evidence import extract_evidence_candidates
from .extraction import DocumentExtractionError, PageText, extract_pages
from .quality import assess_extracted_pages
from .retrieval import DocumentRetrievalError, retrieve_document


@dataclass(frozen=True)
class DocumentProcessResult:
    document_id: str | None
    status: str
    page_count: int = 0
    evidence_count: int = 0
    message: str = ""


@dataclass(frozen=True)
class EvidenceRefreshResult:
    document_count: int
    evidence_count: int
    skipped_count: int = 0


def process_document_for_paper(
    conn: sqlite3.Connection,
    *,
    paper_id: str,
    source_uri: str,
    run_id: str | None = None,
) -> DocumentProcessResult:
    try:
        retrieved = retrieve_document(source_uri)
    except DocumentRetrievalError as exc:
        insert_document_event(
            conn,
            paper_id=paper_id,
            document_id=None,
            run_id=run_id,
            status="error",
            message=str(exc),
        )
        conn.commit()
        return DocumentProcessResult(status="error", document_id=None, message=str(exc))

    content_hash = sha256(retrieved.content).hexdigest()
    document_id = f"doc-{sha256(f'{paper_id}|{content_hash}'.encode('utf-8')).hexdigest()[:16]}"
    try:
        pages = extract_pages(retrieved.content, retrieved.content_type)
    except DocumentExtractionError as exc:
        insert_document(
            conn,
            document_id=document_id,
            paper_id=paper_id,
            run_id=run_id,
            source_uri=retrieved.source_uri,
            content_type=retrieved.content_type,
            content_sha256=content_hash,
            page_count=0,
            status="error",
            error_message=str(exc),
        )
        insert_document_event(
            conn,
            paper_id=paper_id,
            document_id=document_id,
            run_id=run_id,
            status="error",
            message=str(exc),
        )
        conn.commit()
        return DocumentProcessResult(document_id=document_id, status="error", message=str(exc))

    try:
        evidence_items = extract_evidence_candidates(pages, document_id=document_id)
        quality = assess_extracted_pages(
            pages,
            evidence_kinds={item.kind for item in evidence_items},
        )
        if not quality.ok:
            conn.execute("DELETE FROM evidence_items WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM document_pages WHERE document_id = ?", (document_id,))
            insert_document(
                conn,
                document_id=document_id,
                paper_id=paper_id,
                run_id=run_id,
                source_uri=retrieved.source_uri,
                content_type=retrieved.content_type,
                content_sha256=content_hash,
                page_count=len(pages),
                status="error",
                error_message=quality.reason,
            )
            insert_document_event(
                conn,
                paper_id=paper_id,
                document_id=document_id,
                run_id=run_id,
                status="error",
                message=quality.reason,
            )
            conn.commit()
            return DocumentProcessResult(
                document_id=document_id,
                status="error",
                page_count=len(pages),
                evidence_count=len(evidence_items),
                message=quality.reason,
            )
        insert_document(
            conn,
            document_id=document_id,
            paper_id=paper_id,
            run_id=run_id,
            source_uri=retrieved.source_uri,
            content_type=retrieved.content_type,
            content_sha256=content_hash,
            page_count=len(pages),
            status="ok",
        )
        conn.execute("DELETE FROM evidence_items WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM document_pages WHERE document_id = ?", (document_id,))
        for page in pages:
            insert_document_page(
                conn,
                document_id=document_id,
                page_number=page.page_number,
                text=page.text,
            )
        for item in evidence_items:
            insert_evidence_item(
                conn,
                paper_id=paper_id,
                document_id=document_id,
                page_number=item.page_number,
                kind=item.kind,
                label=item.label,
                text=item.text,
                source_locator=item.source_locator,
                confidence=item.confidence,
            )
        insert_document_event(
            conn,
            paper_id=paper_id,
            document_id=document_id,
            run_id=run_id,
            status="ok",
            message=f"Extracted {len(pages)} pages and {len(evidence_items)} evidence items",
        )
        conn.commit()
        return DocumentProcessResult(
            document_id=document_id,
            status="ok",
            page_count=len(pages),
            evidence_count=len(evidence_items),
        )
    except sqlite3.Error:
        conn.rollback()
        raise


def refresh_evidence_from_stored_pages(
    conn: sqlite3.Connection,
    *,
    run_id: str | None = None,
    paper_id: str | None = None,
) -> EvidenceRefreshResult:
    rows = _refresh_targets(conn, run_id=run_id, paper_id=paper_id)
    document_count = 0
    evidence_count = 0
    skipped_count = 0
    try:
        for row in rows:
            pages = [
                PageText(page_number=int(page["page_number"]), text=page["text"])
                for page in conn.execute(
                    """
                    SELECT page_number, text
                    FROM document_pages
                    WHERE document_id = ?
                    ORDER BY page_number ASC
                    """,
                    (row["id"],),
                ).fetchall()
            ]
            if not pages:
                skipped_count += 1
                insert_document_event(
                    conn,
                    paper_id=row["paper_id"],
                    document_id=row["id"],
                    run_id=run_id or row["run_id"],
                    status="skipped",
                    message="No stored pages available for evidence refresh",
                )
                continue
            evidence_items = extract_evidence_candidates(pages, document_id=row["id"])
            conn.execute("DELETE FROM evidence_items WHERE document_id = ?", (row["id"],))
            for item in evidence_items:
                insert_evidence_item(
                    conn,
                    paper_id=row["paper_id"],
                    document_id=row["id"],
                    page_number=item.page_number,
                    kind=item.kind,
                    label=item.label,
                    text=item.text,
                    source_locator=item.source_locator,
                    confidence=item.confidence,
                )
            insert_document_event(
                conn,
                paper_id=row["paper_id"],
                document_id=row["id"],
                run_id=run_id or row["run_id"],
                status="ok",
                message=f"Refreshed {len(evidence_items)} evidence items from stored pages",
            )
            document_count += 1
            evidence_count += len(evidence_items)
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    return EvidenceRefreshResult(
        document_count=document_count,
        evidence_count=evidence_count,
        skipped_count=skipped_count,
    )


def _refresh_targets(
    conn: sqlite3.Connection,
    *,
    run_id: str | None,
    paper_id: str | None,
) -> list[sqlite3.Row]:
    conditions = ["documents.status = 'ok'"]
    params: list[str] = []
    if run_id:
        conditions.append("documents.run_id = ?")
        params.append(run_id)
    if paper_id:
        conditions.append("documents.paper_id = ?")
        params.append(paper_id)
    return conn.execute(
        f"""
        SELECT id, paper_id, run_id
        FROM documents
        WHERE {' AND '.join(conditions)}
        ORDER BY updated_at DESC, id ASC
        """,
        tuple(params),
    ).fetchall()
