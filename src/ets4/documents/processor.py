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
from .extraction import DocumentExtractionError, extract_pages
from .retrieval import DocumentRetrievalError, retrieve_document


@dataclass(frozen=True)
class DocumentProcessResult:
    document_id: str | None
    status: str
    page_count: int = 0
    evidence_count: int = 0
    message: str = ""


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
        evidence_items = extract_evidence_candidates(pages, document_id=document_id)
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
