from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

from .config import AppConfig


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    issue_id: str
    issue_date: str
    created_at: str
    source_snapshot_id: str
    prompt_version: str
    model_policy: dict[str, Any]
    cost_budget: dict[str, Any]
    paper_budget: dict[str, Any]
    allowed_actions: tuple[str, ...]
    force_include: tuple[str, ...]
    force_exclude: tuple[str, ...]
    automation_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_manifest(
    config: AppConfig,
    issue_date: date,
    automation_mode: str = "manual",
    allowed_actions: tuple[str, ...] = ("collect", "triage", "review", "export_draft"),
) -> RunManifest:
    source_snapshot_id = _source_snapshot_id(config)
    issue_id = f"ets4-{issue_date.isoformat()}"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return RunManifest(
        run_id=f"run-{uuid4().hex[:12]}",
        issue_id=issue_id,
        issue_date=issue_date.isoformat(),
        created_at=now,
        source_snapshot_id=source_snapshot_id,
        prompt_version=config.model_policy.prompt_version,
        model_policy={
            "provider": config.model_policy.provider,
            "triage_model": config.model_policy.triage_model,
            "review_model": config.model_policy.review_model,
        },
        cost_budget={"max_total_cost_usd": config.issue.max_total_cost_usd},
        paper_budget={
            "max_candidates_to_triage": config.issue.max_candidates_to_triage,
            "max_papers_to_full_review": config.issue.max_papers_to_full_review,
            "max_short_mentions": config.issue.max_short_mentions,
            "max_deep_dive_drafts": config.issue.max_deep_dive_drafts,
        },
        allowed_actions=allowed_actions,
        force_include=config.issue.force_include,
        force_exclude=config.issue.force_exclude,
        automation_mode=automation_mode,
    )


def _source_snapshot_id(config: AppConfig) -> str:
    payload = "\n".join(
        f"{source.id}|{source.type}|{source.url}|{source.priority}|{source.lookback_days}"
        for source in sorted(config.sources, key=lambda item: item.id)
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:16]
