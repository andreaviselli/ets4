from __future__ import annotations

import re
from dataclasses import dataclass

from .extraction import PageText

HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z][^>]{0,200}>")


@dataclass(frozen=True)
class EvidenceQualityResult:
    ok: bool
    reason: str = ""
    clean_char_count: int = 0
    tag_count: int = 0
    evidence_kind_count: int = 0


def assess_extracted_pages(
    pages: list[PageText],
    *,
    evidence_kinds: set[str],
    min_clean_chars: int = 300,
    min_evidence_kinds: int = 2,
    max_html_tag_count: int = 5,
) -> EvidenceQualityResult:
    text = "\n".join(page.text for page in pages)
    clean_char_count = len(" ".join(text.split()))
    tag_count = len(HTML_TAG_PATTERN.findall(text))
    evidence_kind_count = len(evidence_kinds)
    if not pages:
        return EvidenceQualityResult(ok=False, reason="No extracted pages")
    if clean_char_count < min_clean_chars:
        return EvidenceQualityResult(
            ok=False,
            reason=f"Extracted text too short: {clean_char_count} clean characters",
            clean_char_count=clean_char_count,
            tag_count=tag_count,
            evidence_kind_count=evidence_kind_count,
        )
    if tag_count > max_html_tag_count:
        return EvidenceQualityResult(
            ok=False,
            reason=f"Extracted text appears to contain HTML boilerplate: {tag_count} tags",
            clean_char_count=clean_char_count,
            tag_count=tag_count,
            evidence_kind_count=evidence_kind_count,
        )
    if evidence_kind_count < min_evidence_kinds:
        return EvidenceQualityResult(
            ok=False,
            reason=f"Evidence diversity too low: {evidence_kind_count} evidence kinds",
            clean_char_count=clean_char_count,
            tag_count=tag_count,
            evidence_kind_count=evidence_kind_count,
        )
    return EvidenceQualityResult(
        ok=True,
        clean_char_count=clean_char_count,
        tag_count=tag_count,
        evidence_kind_count=evidence_kind_count,
    )
