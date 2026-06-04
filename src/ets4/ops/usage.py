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
    insert_usage_record(
        conn,
        run_id=run_id,
        stage=stage,
        provider=provider,
        model=model,
        input_tokens=_estimate_tokens(input_text),
        output_tokens=_estimate_tokens(output_text),
        estimated_cost_usd=0.0,
        metadata=metadata,
    )


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
