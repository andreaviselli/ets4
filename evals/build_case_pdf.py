"""Build stable, disposable PDFs from versioned synthetic evaluation manuscripts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import fitz  # type: ignore[import-untyped]

PAGE_BREAK = "<!-- PAGE BREAK -->"


def build_pdf(source: Path, destination: Path) -> str:
    sections = source.read_text(encoding="utf-8").split(PAGE_BREAK)
    document = fitz.open()
    try:
        for section in sections:
            page = document.new_page(width=595, height=842)
            remaining = page.insert_textbox(
                fitz.Rect(54, 48, 541, 794),
                section.strip(),
                fontsize=9.5,
                fontname="helv",
                lineheight=1.2,
            )
            if remaining < 0:
                raise RuntimeError(f"evaluation source overflows a PDF page: {source}")
        document.set_metadata(
            {
                "title": "ETS4 synthetic behavioral evaluation case",
                "author": "ETS4 project",
                "subject": "Versioned synthetic manuscript; not a real research result",
                "creator": "evals/build_case_pdf.py",
                "producer": "PyMuPDF",
                "creationDate": "",
                "modDate": "",
            }
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        document.save(destination, garbage=4, deflate=True, no_new_id=True)
    finally:
        document.close()
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    print(build_pdf(arguments.source, arguments.destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
