from __future__ import annotations

from typing import Any

from .records import ExportRecord


def render_public_issue(*, manifest: dict[str, Any], records: list[ExportRecord]) -> str:
    deep_dives = [record for record in records if record.stage == "deep_dive_draft"]
    short_mentions = [record for record in records if record.stage == "short_mention"]
    lines = [
        "---",
        "layout: post",
        f"title: \"ETS4 Monthly - {manifest['issue_date']}\"",
        f"date: {manifest['issue_date']}",
        "draft: true",
        f"ets4_run_id: \"{manifest['run_id']}\"",
        f"ets4_issue_id: \"{manifest['issue_id']}\"",
        "---",
        "",
        f"# ETS4 Monthly - {manifest['issue_date']}",
        "",
        "_Draft generated for human editorial review. Publication requires manual approval._",
        "",
    ]
    if deep_dives:
        lines.extend(["## Deep Dive Drafts", ""])
        for record in deep_dives:
            lines.extend(_render_public_record(record, heading_level=3))
    if short_mentions:
        lines.extend(["## Short Mentions", ""])
        for record in short_mentions:
            lines.extend(_render_public_record(record, heading_level=3))
    if not records:
        lines.extend(["No papers were selected for draft export.", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_internal_notes(*, manifest: dict[str, Any], records: list[ExportRecord]) -> str:
    lines = [
        f"# ETS4 Internal Notes - {manifest['issue_date']}",
        "",
        f"- Run id: `{manifest['run_id']}`",
        f"- Issue id: `{manifest['issue_id']}`",
        f"- Prompt version: `{manifest['prompt_version']}`",
        f"- Model policy: `{manifest['model_policy']}`",
        "- Final human decision: TODO",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## {record.title}",
                "",
                f"- Paper id: `{record.paper_id}`",
                f"- Stage: `{record.stage}`",
                f"- Rank: {record.rank}",
                f"- Source: {record.canonical_url}",
                f"- Handling-editor decision: `{record.decision.get('decision')}`",
                f"- Deep-dive score: {record.decision.get('deep_dive_score')}",
                f"- Confidence: {record.decision.get('confidence')}",
                "",
                "### Panel Summary",
                "",
                f"- Majority view: {record.decision.get('majority_view')}",
                f"- Minority view: {record.decision.get('minority_view')}",
                f"- Rationale: {record.decision.get('rationale')}",
                "",
                "### Questions For Human Editor",
                "",
            ]
        )
        questions = record.decision.get("questions_for_human") or []
        lines.extend(_bullet_list(questions, empty="No open questions recorded."))
        lines.extend(["", "### Reviewer Reports", ""])
        for report in record.reviewer_reports:
            lines.extend(
                [
                    f"#### {str(report.get('role', 'unknown')).title()}",
                    "",
                    f"- Recommendation: `{report.get('recommendation')}`",
                    f"- Score: {report.get('score')}",
                    f"- Confidence: {report.get('confidence')}",
                    f"- Evidence ids: {_format_ids(report.get('evidence_item_ids') or [])}",
                    f"- Summary: {report.get('summary')}",
                    "",
                ]
            )
        lines.extend(["### Claim Ledger", ""])
        lines.extend(_render_claim_ledger(record))
        lines.extend(["", "### Extracted Evidence", ""])
        for item in _evidence_items(record):
            lines.extend(
                [
                    (
                        f"- E{item['id']} `{item['kind']}` p{item['page_number']}: "
                        f"{_one_line(item['text'])}"
                    )
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_public_record(record: ExportRecord, *, heading_level: int) -> list[str]:
    marker = "#" * heading_level
    evidence = _evidence_items(record)
    primary = evidence[:3]
    lines = [
        f"{marker} {record.title}",
        "",
        f"Source: [{record.canonical_url}]({record.canonical_url})",
        "",
        (
            f"Handling-editor decision: `{record.decision.get('decision')}` "
            f"(score {record.decision.get('deep_dive_score')}, "
            f"confidence {record.decision.get('confidence')}). "
            f"Evidence: {_format_ids(record.decision.get('evidence_item_ids') or [])}."
        ),
        "",
    ]
    for item in primary:
        lines.extend(
            [
                (
                    f"{_one_line(item['text'])} "
                    f"[E{item['id']}, p. {item['page_number']}]"
                ),
                "",
            ]
        )
    lines.extend(["Caveats for the editor:", ""])
    questions = record.decision.get("questions_for_human") or []
    lines.extend(_bullet_list(questions, empty="No blocking caveats recorded."))
    lines.extend(["", "Claim ledger:", ""])
    lines.extend(_render_claim_ledger(record))
    lines.append("")
    return lines


def _render_claim_ledger(record: ExportRecord) -> list[str]:
    ledger = []
    for item in _evidence_items(record)[:10]:
        ledger.append(
            (
                f"- Claim candidate: {_one_line(item['text'])} "
                f"Evidence: E{item['id']} ({item['source_locator']})."
            )
        )
    return ledger or ["- No evidence-backed claims available."]


def _evidence_items(record: ExportRecord) -> list[dict[str, Any]]:
    return list(record.dossier.get("evidence_items") or [])


def _bullet_list(values: list[str], *, empty: str) -> list[str]:
    if not values:
        return [f"- {empty}"]
    return [f"- {value}" for value in values]


def _format_ids(values: list[int]) -> str:
    if not values:
        return "none"
    return ", ".join(f"E{value}" for value in values)


def _one_line(value: str, *, limit: int = 280) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
