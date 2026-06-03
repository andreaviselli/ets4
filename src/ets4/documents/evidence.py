from __future__ import annotations

from dataclasses import dataclass

from .extraction import PageText


@dataclass(frozen=True)
class EvidenceCandidate:
    page_number: int
    kind: str
    label: str
    text: str
    source_locator: str
    confidence: float = 1.0


KEYWORD_RULES = (
    ("dataset", ("dataset", "data set", "sample", "panel", "observations")),
    ("metric", ("rmse", "mae", "crps", "brier", "accuracy", "score", "metric")),
    ("baseline", ("baseline", "benchmark", "compared with", "comparison")),
    ("limitation", ("limitation", "caveat", "fails", "weakness", "not robust")),
    ("method", ("model", "method", "estimator", "algorithm", "architecture")),
    ("code", ("code", "repository", "github", "replication")),
)


def extract_evidence_candidates(pages: list[PageText], *, document_id: str) -> list[EvidenceCandidate]:
    candidates = []
    for page in pages:
        for paragraph in _paragraphs(page.text):
            kind = _classify(paragraph)
            if kind is None:
                continue
            candidates.append(
                EvidenceCandidate(
                    page_number=page.page_number,
                    kind=kind,
                    label=kind.replace("_", " ").title(),
                    text=paragraph,
                    source_locator=f"{document_id}:p{page.page_number}",
                    confidence=0.7,
                )
            )
    return candidates


def _paragraphs(text: str) -> list[str]:
    chunks = []
    for part in text.split("\n\n"):
        paragraph = " ".join(part.split())
        if len(paragraph) >= 40:
            chunks.append(paragraph)
    for line in text.splitlines():
        paragraph = " ".join(line.split())
        if len(paragraph) >= 40 and paragraph not in chunks:
            chunks.append(paragraph)
    return chunks


def _classify(text: str) -> str | None:
    lowered = text.lower()
    for kind, keywords in KEYWORD_RULES:
        if any(keyword in lowered for keyword in keywords):
            return kind
    return None
