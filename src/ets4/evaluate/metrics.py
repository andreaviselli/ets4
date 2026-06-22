from __future__ import annotations

import json
import sqlite3
from typing import Any

from .labels import PaperLabel


def evaluate_paper(conn: sqlite3.Connection, *, run_id: str, label: PaperLabel) -> dict[str, Any]:
    paper = _fetch_one(
        conn,
        """
        SELECT title
        FROM papers
        WHERE id = ?
        """,
        (label.paper_id,),
    )
    triage = _fetch_one(
        conn,
        """
        SELECT decision, category_hint, score, confidence
        FROM triage_reviews
        WHERE run_id = ? AND paper_id = ?
        """,
        (run_id, label.paper_id),
    )
    evidence_rows = conn.execute(
        """
        SELECT id, kind
        FROM evidence_items
        WHERE paper_id = ?
        """,
        (label.paper_id,),
    ).fetchall()
    reports = conn.execute(
        """
        SELECT reviewer_role, recommendation, score, evidence_item_ids_json
        FROM reviewer_reports
        WHERE run_id = ? AND paper_id = ? AND status = 'ok'
        """,
        (run_id, label.paper_id),
    ).fetchall()
    decision = _fetch_one(
        conn,
        """
        SELECT decision, deep_dive_score, confidence, memo_json
        FROM editorial_decisions
        WHERE run_id = ? AND paper_id = ? AND status = 'ok'
        """,
        (run_id, label.paper_id),
    )
    selections = {
        str(row["selection_stage"]): int(row["rank"])
        for row in conn.execute(
            """
            SELECT selection_stage, rank
            FROM candidate_selections
            WHERE run_id = ? AND paper_id = ?
            """,
            (run_id, label.paper_id),
        ).fetchall()
    }

    evidence_ids = {int(row["id"]) for row in evidence_rows}
    evidence_kinds = {str(row["kind"]) for row in evidence_rows}
    required_kinds = set(label.required_evidence_kinds)
    covered_required_kinds = required_kinds & evidence_kinds
    citations = _reviewer_citations(reports)
    invalid_citations = [citation for citation in citations if citation not in evidence_ids]
    reviewer_scores = [float(row["score"]) for row in reports]
    reviewer_recommendations = {str(row["recommendation"]) for row in reports}
    memo = _json_dict(decision["memo_json"]) if decision else {}
    system_publication_track = memo.get("publication_track") or _system_publication_track(
        decision["decision"] if decision else None,
        selections=selections,
    )

    return {
        "paper_id": label.paper_id,
        "title": paper["title"] if paper else None,
        "label": {
            "relevance_label": label.relevance_label,
            "audience_fit": label.audience_fit,
            "application_type": label.application_type,
            "economic_relevance": label.economic_relevance,
            "forecasting_contribution": label.forecasting_contribution,
            "publication_track": label.publication_track,
            "social_hook_potential": label.social_hook_potential,
            "expected_category": label.expected_category,
            "expected_triage_decision": label.expected_triage_decision,
            "expected_editorial_decision": label.expected_editorial_decision,
            "expected_deep_dive": label.expected_deep_dive,
            "expected_short_mention": label.expected_short_mention,
            "required_evidence_kinds": list(label.required_evidence_kinds),
            "hard_negative": label.hard_negative,
            "high_value": label.high_value,
        },
        "triage": {
            "present": triage is not None,
            "decision": triage["decision"] if triage else None,
            "category_hint": triage["category_hint"] if triage else None,
            "score": float(triage["score"]) if triage else None,
            "decision_correct": _equals_optional(
                triage["decision"] if triage else None,
                label.expected_triage_decision,
            ),
            "category_correct": _equals_optional(
                triage["category_hint"] if triage else None,
                label.expected_category,
            ),
        },
        "selection": {
            "selected_full_review": "full_review" in selections,
            "selected_deep_dive": "deep_dive_draft" in selections,
            "selected_short_mention": "short_mention" in selections,
            "deep_dive_correct": _equals_optional(
                "deep_dive_draft" in selections,
                label.expected_deep_dive,
            ),
            "short_mention_correct": _equals_optional(
                "short_mention" in selections,
                label.expected_short_mention,
            ),
        },
        "evidence": {
            "evidence_count": len(evidence_rows),
            "evidence_kinds": sorted(evidence_kinds),
            "required_kind_count": len(required_kinds),
            "covered_required_kind_count": len(covered_required_kinds),
            "required_kind_coverage": _ratio(len(covered_required_kinds), len(required_kinds)),
            "missing_required_kinds": sorted(required_kinds - evidence_kinds),
        },
        "review": {
            "reviewer_report_count": len(reports),
            "citation_count": len(citations),
            "invalid_citation_count": len(invalid_citations),
            "citation_coverage": _ratio(
                sum(1 for row in reports if _row_citations(row)),
                len(reports),
            ),
            "invalid_citation_rate": _ratio(len(invalid_citations), len(citations)),
            "reviewer_disagreement": (
                max(reviewer_scores) - min(reviewer_scores) if reviewer_scores else None
            ),
            "recommendation_diversity": len(reviewer_recommendations),
        },
        "editorial": {
            "present": decision is not None,
            "decision": decision["decision"] if decision else None,
            "deep_dive_score": float(decision["deep_dive_score"]) if decision else None,
            "publication_track": system_publication_track,
            "publication_track_correct": _equals_optional(
                system_publication_track,
                label.publication_track,
            ),
            "decision_correct": _equals_optional(
                decision["decision"] if decision else None,
                label.expected_editorial_decision,
            ),
            "minority_view": memo.get("minority_view"),
            "hidden_disagreement": (
                bool(len(reviewer_recommendations) > 1)
                and str(memo.get("minority_view", "")).startswith("No material")
            ),
        },
    }


def aggregate_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "labeled_papers": len(items),
        "triage": {
            "decision_accuracy": _mean_optional(
                item["triage"]["decision_correct"] for item in items
            ),
            "category_accuracy": _mean_optional(
                item["triage"]["category_correct"] for item in items
            ),
            "selected_precision": _precision(
                selected=[
                    item["selection"]["selected_full_review"]
                    for item in items
                ],
                positives=[item["label"]["relevance_label"] != "not_relevant" for item in items],
            ),
            "relevant_recall": _recall(
                selected=[
                    item["selection"]["selected_full_review"]
                    for item in items
                ],
                positives=[item["label"]["relevance_label"] != "not_relevant" for item in items],
            ),
            "hard_negative_false_positive_rate": _ratio(
                sum(
                    1
                    for item in items
                    if item["label"]["hard_negative"] and item["selection"]["selected_full_review"]
                ),
                sum(1 for item in items if item["label"]["hard_negative"]),
            ),
            "high_value_false_negative_count": sum(
                1
                for item in items
                if item["label"]["high_value"] and not item["selection"]["selected_full_review"]
            ),
        },
        "evidence": {
            "required_kind_coverage": _mean_optional(
                item["evidence"]["required_kind_coverage"] for item in items
            ),
            "papers_missing_required_evidence": sum(
                1 for item in items if item["evidence"]["missing_required_kinds"]
            ),
        },
        "review": {
            "editorial_decision_accuracy": _mean_optional(
                item["editorial"]["decision_correct"] for item in items
            ),
            "citation_coverage": _mean_optional(
                item["review"]["citation_coverage"] for item in items
            ),
            "invalid_citation_rate": _mean_optional(
                item["review"]["invalid_citation_rate"] for item in items
            ),
            "average_reviewer_disagreement": _mean_optional(
                item["review"]["reviewer_disagreement"] for item in items
            ),
            "hidden_disagreement_count": sum(
                1 for item in items if item["editorial"]["hidden_disagreement"]
            ),
        },
        "selection": {
            "deep_dive_accuracy": _mean_optional(
                item["selection"]["deep_dive_correct"] for item in items
            ),
            "short_mention_accuracy": _mean_optional(
                item["selection"]["short_mention_correct"] for item in items
            ),
        },
        "rubric": {
            "publication_track_accuracy": _mean_optional(
                item["editorial"]["publication_track_correct"] for item in items
            ),
            "audience_fit_distribution": _distribution(
                item["label"]["audience_fit"] for item in items
            ),
            "application_type_distribution": _distribution(
                item["label"]["application_type"] for item in items
            ),
            "economic_relevance_distribution": _distribution(
                item["label"]["economic_relevance"] for item in items
            ),
            "forecasting_contribution_distribution": _distribution(
                item["label"]["forecasting_contribution"] for item in items
            ),
            "publication_track_distribution": _distribution(
                item["label"]["publication_track"] for item in items
            ),
            "social_hook_potential_distribution": _distribution(
                item["label"]["social_hook_potential"] for item in items
            ),
        },
    }


def _fetch_one(conn: sqlite3.Connection, query: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
    return conn.execute(query, params).fetchone()


def _reviewer_citations(rows: list[sqlite3.Row]) -> list[int]:
    citations: list[int] = []
    for row in rows:
        citations.extend(_row_citations(row))
    return citations


def _row_citations(row: sqlite3.Row) -> list[int]:
    return [int(value) for value in json.loads(row["evidence_item_ids_json"])]


def _json_dict(value: str) -> dict[str, Any]:
    loaded = json.loads(value)
    return loaded if isinstance(loaded, dict) else {}


def _equals_optional(actual: Any, expected: Any) -> bool | None:
    if expected is None:
        return None
    return actual == expected


def _system_publication_track(
    editorial_decision: Any,
    *,
    selections: dict[str, int],
) -> str | None:
    decision = str(editorial_decision) if editorial_decision is not None else None
    if decision == "full_deep_dive" or "deep_dive_draft" in selections:
        return "deep_dive"
    if decision == "short_mention" or "short_mention" in selections:
        return "applied_note"
    if decision in {"watchlist", "needs_human_adjudication"}:
        return "methods_watch"
    if decision == "reject":
        return "reject"
    if not selections:
        return "reject"
    return None


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 4)


def _mean_optional(values: Any) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 4)


def _distribution(values: Any) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for value in values:
        if value is None:
            continue
        key = str(value)
        distribution[key] = distribution.get(key, 0) + 1
    return dict(sorted(distribution.items()))


def _precision(*, selected: list[bool], positives: list[bool]) -> float | None:
    selected_count = sum(selected)
    if not selected_count:
        return None
    true_positive_count = sum(
        1
        for is_selected, is_positive in zip(selected, positives)
        if is_selected and is_positive
    )
    return round(true_positive_count / selected_count, 4)


def _recall(*, selected: list[bool], positives: list[bool]) -> float | None:
    positive_count = sum(positives)
    if not positive_count:
        return None
    true_positive_count = sum(
        1
        for is_selected, is_positive in zip(selected, positives)
        if is_selected and is_positive
    )
    return round(true_positive_count / positive_count, 4)
