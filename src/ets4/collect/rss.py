from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ets4.config import SourceConfig


@dataclass(frozen=True)
class PaperCandidate:
    paper_id: str
    title: str
    canonical_url: str
    abstract: str
    authors: str
    source_id: str
    published_date: str | None


def collect_rss_source(source: SourceConfig) -> list[PaperCandidate]:
    response = requests.get(source.url, timeout=20)
    response.raise_for_status()
    if "utf-8" in response.text.lower() or "<?xml" in response.text:
        response.encoding = "utf-8"
    feed = feedparser.parse(response.text)
    cutoff = datetime.now(timezone.utc) - timedelta(days=source.lookback_days)
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
    paper_id = _paper_id(link, title)
    return PaperCandidate(
        paper_id=paper_id,
        title=title,
        canonical_url=link,
        abstract=abstract,
        authors=_authors(entry),
        source_id=source.id,
        published_date=published_date,
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


def _paper_id(link: str, title: str) -> str:
    return sha256(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]
