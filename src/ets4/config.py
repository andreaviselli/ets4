from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - covered by Python version matrix in packaging
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True)
class IssueConfig:
    max_candidates_to_triage: int = 250
    max_papers_to_full_review: int = 20
    max_short_mentions: int = 8
    max_deep_dive_drafts: int = 3
    max_total_cost_usd: float = 10.0
    force_include: tuple[str, ...] = ()
    force_exclude: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    type: str
    url: str
    domain: str = "unknown"
    priority: str = "medium"
    lookback_days: int = 30


@dataclass(frozen=True)
class ModelPolicy:
    provider: str = "fake"
    triage_model: str = "fake-triage-v1"
    review_model: str = "fake-review-v1"
    prompt_version: str = "dev"


@dataclass(frozen=True)
class AppConfig:
    issue: IssueConfig = field(default_factory=IssueConfig)
    model_policy: ModelPolicy = field(default_factory=ModelPolicy)
    sources: tuple[SourceConfig, ...] = ()


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("rb") as f:
        raw = tomllib.load(f)

    issue = _load_issue(raw.get("issue", {}))
    model_policy = _load_model_policy(raw.get("model_policy", {}))
    sources = tuple(_load_source(item) for item in _source_items(raw))
    return AppConfig(issue=issue, model_policy=model_policy, sources=sources)


def _load_issue(raw: dict[str, Any]) -> IssueConfig:
    return IssueConfig(
        max_candidates_to_triage=int(raw.get("max_candidates_to_triage", 250)),
        max_papers_to_full_review=int(raw.get("max_papers_to_full_review", 20)),
        max_short_mentions=int(raw.get("max_short_mentions", 8)),
        max_deep_dive_drafts=int(raw.get("max_deep_dive_drafts", 3)),
        max_total_cost_usd=float(raw.get("max_total_cost_usd", 10.0)),
        force_include=tuple(raw.get("force_include", ())),
        force_exclude=tuple(raw.get("force_exclude", ())),
    )


def _load_model_policy(raw: dict[str, Any]) -> ModelPolicy:
    return ModelPolicy(
        provider=str(raw.get("provider", "fake")),
        triage_model=str(raw.get("triage_model", "fake-triage-v1")),
        review_model=str(raw.get("review_model", "fake-review-v1")),
        prompt_version=str(raw.get("prompt_version", "dev")),
    )


def _source_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
    if "sources" in raw:
        return list(raw["sources"])
    if "feeds" in raw:
        return list(raw["feeds"])
    return []


def _load_source(raw: dict[str, Any]) -> SourceConfig:
    name = str(raw["name"])
    source_id = str(raw.get("id") or _slugify(name))
    return SourceConfig(
        id=source_id,
        name=name,
        type=str(raw.get("type", "rss")),
        url=str(raw["url"]),
        domain=str(raw.get("domain", "unknown")),
        priority=str(raw.get("priority", "medium")),
        lookback_days=int(raw.get("lookback_days", 30)),
    )


def _slugify(value: str) -> str:
    chars = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-")

