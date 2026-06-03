from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ets4.config import SourceConfig
from ets4.identity import canonicalize_url, extract_arxiv_id, extract_doi, stable_paper_id


@dataclass(frozen=True)
class PaperCandidate:
    paper_id: str
    title: str
    canonical_url: str
    abstract: str
    authors: str
    source_id: str
    published_date: str | None
    doi: str | None
    arxiv_id: str | None


def collect_rss_source(source: SourceConfig) -> list[PaperCandidate]:
    response = requests.get(source.url, timeout=20)
    response.raise_for_status()
    if "utf-8" in response.text.lower() or "<?xml" in response.text:
        response.encoding = "utf-8"
    return parse_rss_content(source, response.text)


def parse_rss_content(
    source: SourceConfig,
    content: str,
    *,
    now: datetime | None = None,
) -> list[PaperCandidate]:
    feed = feedparser.parse(content)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=source.lookback_days)
    candidates = []
    for entry in feed.entries:
        candidate = _candidate_from_entry(source, entry, cutoff)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _candidate_from_entry(
    source: SourceConfig, entry: Any, cutoff: datetime
) -> PaperCandidate | None:
    published = getattr(entry, "published", getattr(entry, "updated", None))
    published_date = None
    if published:
        try:
            parsed = dateparser.parse(published)
        except (TypeError, ValueError, dateparser.ParserError):
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < cutoff:
                return None
            published_date = parsed.date().isoformat()

    title = str(getattr(entry, "title", "")).strip()
    link = str(getattr(entry, "link", "")).strip()
    if not title or not link:
        return None
    abstract = _clean_summary(str(getattr(entry, "summary", "") or ""))
    canonical_url = canonicalize_url(link)
    entry_id = str(getattr(entry, "id", "") or "")
    doi = extract_doi(title, abstract, link, entry_id)
    arxiv_id = extract_arxiv_id(title, abstract, link, entry_id)
    paper_id = stable_paper_id(doi or "", arxiv_id or "", canonical_url, title)
    return PaperCandidate(
        paper_id=paper_id,
        title=title,
        canonical_url=canonical_url,
        abstract=abstract,
        authors=_authors(entry),
        source_id=source.id,
        published_date=published_date,
        doi=doi,
        arxiv_id=arxiv_id,
    )


def _clean_summary(summary: str) -> str:
    if "<" in summary and ">" in summary:
        return BeautifulSoup(summary, "html.parser").get_text(separator=" ", strip=True)
    return " ".join(summary.split())


def _authors(entry: Any) -> str:
    authors = getattr(entry, "authors", None)
    if authors:
        names = [author.get("name", "") for author in authors if author.get("name")]
        if names:
            return ", ".join(names)
    author = getattr(entry, "author", None)
    return str(author) if author else ""
