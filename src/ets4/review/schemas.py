from __future__ import annotations

from typing import Any

REVIEWER_ROLES = (
    "relevance",
    "methods",
    "evidence",
    "practitioner",
    "transferability",
)

REVIEWER_RECOMMENDATIONS = {
    "support_deep_dive",
    "support_short_mention",
    "watchlist",
    "needs_editor",
    "reject",
}

EDITORIAL_DECISIONS = {
    "full_deep_dive",
    "short_mention",
    "watchlist",
    "needs_human_adjudication",
    "reject",
}
PUBLICATION_TRACKS = {
    "deep_dive",
    "applied_note",
    "methods_watch",
    "reject",
}

REVIEWER_REPORT_SCHEMA: dict[str, Any] = {
    "required": (
        "role",
        "recommendation",
        "score",
        "confidence",
        "summary",
        "strengths",
        "weaknesses",
        "required_evidence",
        "evidence_item_ids",
        "questions_for_editor",
    )
}

EDITORIAL_DECISION_SCHEMA: dict[str, Any] = {
    "required": (
        "decision",
        "publication_track",
        "deep_dive_score",
        "confidence",
        "rationale",
        "majority_view",
        "minority_view",
        "evidence_item_ids",
        "questions_for_human",
    )
}


def validate_reviewer_report(payload: dict[str, Any]) -> None:
    missing = [key for key in REVIEWER_REPORT_SCHEMA["required"] if key not in payload]
    if missing:
        raise ValueError(f"Reviewer report missing required keys: {', '.join(missing)}")
    if payload["role"] not in REVIEWER_ROLES:
        raise ValueError(f"Unknown reviewer role: {payload['role']}")
    if payload["recommendation"] not in REVIEWER_RECOMMENDATIONS:
        raise ValueError(f"Unknown reviewer recommendation: {payload['recommendation']}")
    _validate_score("score", payload["score"])
    _validate_score("confidence", payload["confidence"], upper=1.0)
    if not isinstance(payload["evidence_item_ids"], list):
        raise ValueError("Reviewer report evidence_item_ids must be a list")


def validate_editorial_decision(payload: dict[str, Any]) -> None:
    missing = [key for key in EDITORIAL_DECISION_SCHEMA["required"] if key not in payload]
    if missing:
        raise ValueError(f"Editorial decision missing required keys: {', '.join(missing)}")
    if payload["decision"] not in EDITORIAL_DECISIONS:
        raise ValueError(f"Unknown editorial decision: {payload['decision']}")
    if payload["publication_track"] not in PUBLICATION_TRACKS:
        raise ValueError(f"Unknown publication track: {payload['publication_track']}")
    _validate_score("deep_dive_score", payload["deep_dive_score"])
    _validate_score("confidence", payload["confidence"], upper=1.0)
    if not isinstance(payload["evidence_item_ids"], list):
        raise ValueError("Editorial decision evidence_item_ids must be a list")


def _validate_score(name: str, value: Any, *, upper: float = 10.0) -> None:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    if not 0 <= float(value) <= upper:
        raise ValueError(f"{name} must be between 0 and {upper}")
