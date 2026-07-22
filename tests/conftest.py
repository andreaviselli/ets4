from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from ets4.config import ReviewSettings
from ets4.ingestion.models import ManuscriptPackage
from ets4.ingestion.pdf import ManuscriptIngestor


def write_test_pdf(path: Path, text: str | None = None, pages: int = 2) -> Path:
    document = fitz.open()
    body = text or (
        "Synthetic economic time-series forecasting manuscript. "
        "We compare recursive forecasts using a held-out evaluation sample, report "
        "forecast errors, "
        "and discuss uncertainty, data revisions, limitations, and reproducibility. "
    )
    for index in range(pages):
        page = document.new_page()
        page.insert_textbox(
            fitz.Rect(50, 50, 545, 790),
            f"Page {index + 1}\n" + body * 4,
            fontsize=10,
        )
    document.save(path)
    document.close()
    return path


@pytest.fixture
def manuscript_path(tmp_path: Path) -> Path:
    return write_test_pdf(tmp_path / "manuscript.pdf")


@pytest.fixture
def manuscript(manuscript_path: Path) -> ManuscriptPackage:
    return ManuscriptIngestor(ReviewSettings()).ingest(manuscript_path)


@pytest.fixture
def public_resolver():
    def resolve(_host: str, port: int, **_kwargs: object):
        return [(2, 1, 6, "", ("93.184.216.34", port))]

    return resolve
