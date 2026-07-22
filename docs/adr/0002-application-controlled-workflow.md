# ADR 0002: application-controlled stateless agent orchestration

Status: accepted on 2026-07-14.

## Context

The protocol requires strict context isolation, exact fixed-panel fan-in, validation, bounded failure recovery, and resumability without repeating paid calls.

## Decision

Use an explicit Python state machine and stateless provider calls. The workflow constructs every context, launches a bounded referee pool, persists each successful stage atomically, and alone decides when the final editor may run. Do not use free-form agent handoffs or provider-hosted conversation threads.

## Consequences

Operational independence is testable. The final editor cannot see partial panels, and a model cannot call tools or choose routing. The implementation is more explicit than an Agent SDK abstraction but remains provider-neutral.

## Reversal

A workflow runtime or Agent SDK may replace this implementation only if it preserves and tests the same context, fan-in, atomicity, idempotency, and provider boundaries.
