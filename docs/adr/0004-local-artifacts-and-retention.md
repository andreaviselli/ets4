# ADR 0004: atomic local run artifacts and explicit raw retention

Status: accepted on 2026-07-14.

## Context

ETS4 must be inspectable, resumable, and auditable while manuscripts and model responses may be confidential. A database is unnecessary for the first single-user local interface.

## Decision

Use one isolated directory per run. Persist the canonical manuscript, normalized pages, validated JSON, Markdown, usage, manifest, and minimal event log. Write stage artifacts atomically before manifest advancement. Store raw provider responses separately and make retention configurable; enable it by default only for the local profile.

## Consequences

Runs are portable and easy to inspect. Resume can recover an artifact written immediately before a process crash. Users are responsible for filesystem permissions and deletion. Hosted storage needs a distinct design.

## Reversal

Move state to a transactional database/object store when multiple workers or users require locking, authorization, lifecycle jobs, and queries. Preserve the same exported run contract and checksums.
