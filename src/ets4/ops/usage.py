from __future__ import annotations

import sqlite3
from typing import Any

from ets4.store.db import insert_usage_record


def record_fake_usage(
    conn: sqlite3.Connection,
    *,
    run_id: str | None,
    stage: str,
    provider: str,
    model: str,
    input_text: str,
    output_text: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    record_model_usage(
        conn,
        run_id=run_id,
        stage=stage,
        provider=provider,
        model=model,
        input_text=input_text,
        output_text=output_text,
        metadata=metadata,
    )


def record_model_usage(
    conn: sqlite3.Connection,
    *,
    run_id: str | None,
    stage: str,
    provider: str,
    model: str,
    input_text: str,
    output_text: str,
    metadata: dict[str, Any] | None = None,
    usage: Any | None = None,
) -> None:
    usage_metadata = dict(metadata or {})
    input_tokens = _estimate_tokens(input_text)
    output_tokens = _estimate_tokens(output_text)
    estimated_cost_usd = 0.0
    if usage is not None:
        input_tokens = int(usage.input_tokens or input_tokens)
        output_tokens = int(usage.output_tokens or output_tokens)
        estimated_cost_usd = float(usage.estimated_cost_usd)
        usage_metadata.update(usage.metadata)
        if usage.total_tokens is not None:
            usage_metadata["total_tokens"] = usage.total_tokens

    insert_usage_record(
        conn,
        run_id=run_id,
        stage=stage,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        metadata=usage_metadata,
    )


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
