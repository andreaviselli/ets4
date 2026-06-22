from __future__ import annotations

from datetime import date
from pathlib import Path

import fitz

from ets4.config import load_config
from ets4.documents.evidence import extract_evidence_candidates
from ets4.documents.extraction import PageText, extract_pages
from ets4.documents.processor import process_document_for_paper
from ets4.documents.quality import assess_extracted_pages
from ets4.documents.retrieval import retrieve_document
from ets4.documents.resolver import resolve_document_uri
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


def test_extract_evidence_candidates_recognizes_domain_specific_kinds() -> None:
    pages = [
        PageText(
            page_number=1,
            text=(
                "Alternative scenarios rely on expert judgement during stress testing.\n\n"
                "The structural break during Covid-19 changed volatility and trading risk."
            ),
        )
    ]

    candidates = extract_evidence_candidates(pages, document_id="doc-1")

    assert {
        candidate.kind for candidate in candidates
    } >= {"scenario", "judgement", "structural_break", "Covid-19", "volatility", "trading"}


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


def test_arxiv_abs_url_resolves_to_pdf() -> None:
    assert (
        resolve_document_uri("https://arxiv.org/abs/2509.19663")
        == "https://arxiv.org/pdf/2509.19663.pdf"
    )


def test_http_html_landing_page_resolves_pdf_link(monkeypatch) -> None:
    class Response:
        def __init__(self, content: bytes, content_type: str):
            self.content = content
            self.text = content.decode("utf-8", errors="replace")
            self.headers = {"content-type": content_type}

        def raise_for_status(self) -> None:
            return None

    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        if url.endswith("paper.htm"):
            return Response(
                b'<html><body><a href="/files/paper.pdf">Full Paper</a></body></html>',
                "text/html",
            )
        return Response(b"%PDF-1.4 fake", "application/pdf")

    monkeypatch.setattr("ets4.documents.retrieval.requests.get", fake_get)

    result = retrieve_document("https://example.test/paper.htm")

    assert result.source_uri == "https://example.test/files/paper.pdf"
    assert result.content_type == "application/pdf"
    assert calls == [
        ("https://example.test/paper.htm", 30),
        ("https://example.test/files/paper.pdf", 30),
    ]


def test_html_extraction_removes_boilerplate() -> None:
    fixture = Path("tests/fixtures/documents/sample.html")

    pages = extract_pages(fixture.read_bytes(), "text/html")
    text = "\n".join(page.text for page in pages)
    normalized = " ".join(text.split())

    assert "monthly macroeconomic observations" in normalized
    assert "ARIMA baseline" in normalized
    assert "window.analytics" not in text
    assert "Search navigation" not in text


def test_quality_gate_rejects_html_boilerplate() -> None:
    pages = [
        PageText(
            page_number=1,
            text=(
                "<head><title>Paper</title></head> "
                "<div>Search navigation share bookmark</div> " * 20
            ),
        )
    ]

    result = assess_extracted_pages(pages, evidence_kinds=set())

    assert result.ok is False
    assert "HTML boilerplate" in result.reason


def test_process_html_document_extracts_clean_evidence(tmp_path) -> None:
    db_path = tmp_path / "ets4.sqlite"
    fixture = Path("tests/fixtures/documents/sample.html")
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
        stored = conn.execute("SELECT text FROM document_pages").fetchone()["text"]
        assert "<html" not in stored.lower()
        assert conn.execute("SELECT COUNT(*) FROM evidence_items").fetchone()[0] >= 4


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
