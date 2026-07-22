# ADR 0004: local run files and clear raw-response retention

Status: accepted on 2026-07-14.

## Context

ETS4 must be easy to inspect and resume, while manuscripts and responses may be confidential. A database is unnecessary for the first single-user local tool.

## Decision

Use one directory per run. Save the original paper, page text, checked JSON, Markdown, usage, manifest, and a small event log. Finish each stage file before changing the manifest. Keep raw responses in a separate folder and let the user disable them; enable them by default only for local runs.

## Result

Runs are easy to inspect and move. Resume can find a stage file written just before a process stopped. Users control local permissions and deletion. Hosting needs a different storage design.

## Revisit if

Several workers or users need locking, access rules, automatic deletion, or database queries. Keep the same exported run files and checksums even if internal storage changes.
