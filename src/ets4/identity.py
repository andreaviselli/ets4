from __future__ import annotations

import re
from difflib import SequenceMatcher
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
ARXIV_PATTERN = re.compile(
    r"(?:arxiv:|arxiv\.org/(?:abs|pdf)/)?(?P<id>\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    query = urlencode(
        sorted((key, value) for key, value in parse_qsl(parsed.query) if key not in TRACKING_PARAMS)
    )
    path = parsed.path.rstrip("/")
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            query,
            "",
        )
    )


def normalize_title(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return " ".join(words)


def title_similarity(left: str, right: str) -> float:
    left_norm = normalize_title(left)
    right_norm = normalize_title(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def extract_doi(*values: str) -> str | None:
    for value in values:
        match = DOI_PATTERN.search(value or "")
        if match:
            return match.group(0).rstrip(".").lower()
    return None


def extract_arxiv_id(*values: str) -> str | None:
    for value in values:
        match = ARXIV_PATTERN.search(value or "")
        if match:
            return match.group("id")
    return None


def stable_paper_id(*values: str) -> str:
    payload = "|".join(value for value in values if value)
    return sha256(payload.encode("utf-8")).hexdigest()[:16]

