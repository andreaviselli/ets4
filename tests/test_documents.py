from __future__ import annotations

from datetime import date
from pathlib import Path

import fitz

from ets4.config import load_config
from ets4.documents.extraction import extract_pages
from ets4.documents.processor import process_document_for_paper
from ets4.manifest import create_manifest
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper


def test_process_text_document_extracts_pages_and_evidence(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    fixture = Path("tests/fixtures/documents/sample.txt")
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(db_path) as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_paper(
            conn,
            paper_id="paper-1",
            title="Inflation forecasting",
            canonical_url="https://example.test/paper-1",
        )
        result = process_document_for_paper(
            conn,
            paper_id="paper-1",
            source_uri=str(fixture),
            run_id=manifest.run_id,
        )

        assert result.status == "ok"
        assert result.page_count == 2
        assert result.evidence_count >= 4
        assert conn.execute("SELECT COUNT(*) FROM document_pages").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM evidence_items").fetchone()[0] >= 4
        assert conn.execute("SELECT status FROM document_events").fetchone()[0] == "ok"


def test_pdf_extraction_preserves_pages(tmp_path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "The dataset has monthly inflation observations.")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "The model is compared with a baseline using RMSE.")
    doc.save(pdf_path)
    doc.close()

    pages = extract_pages(pdf_path.read_bytes(), "application/pdf")

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "dataset" in pages[0].text.lower()
    assert pages[1].page_number == 2
    assert "baseline" in pages[1].text.lower()


def test_process_broken_pdf_records_failure(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    fixture = Path("tests/fixtures/documents/broken.pdf")
    config = load_config("config/feeds.example.toml")
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(db_path) as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_paper(
            conn,
            paper_id="paper-1",
            title="Inflation forecasting",
            canonical_url="https://example.test/paper-1",
        )
        result = process_document_for_paper(
            conn,
            paper_id="paper-1",
            source_uri=str(fixture),
            run_id=manifest.run_id,
        )

        assert result.status == "error"
        assert conn.execute("SELECT status FROM documents").fetchone()[0] == "error"
        event = conn.execute("SELECT status, message FROM document_events").fetchone()
        assert event["status"] == "error"
        assert "PDF extraction failed" in event["message"]

