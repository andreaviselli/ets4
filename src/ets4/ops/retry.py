from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryConfig:
    attempts: int = 3
    backoff_seconds: float = 0.5


def retry_call(
    fn: Callable[[], T],
    *,
    config: RetryConfig = RetryConfig(),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    if config.attempts < 1:
        raise ValueError("Retry attempts must be at least 1")
    last_error: Exception | None = None
    for attempt in range(1, config.attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt == config.attempts:
                break
            sleep(config.backoff_seconds * (2 ** (attempt - 1)))
    assert last_error is not None
    raise last_error
