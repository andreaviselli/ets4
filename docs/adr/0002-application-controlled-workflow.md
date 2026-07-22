# ADR 0002: Python controls separate model calls

Status: accepted on 2026-07-14.

## Context

ETS4 must keep referee contexts apart, wait for the exact fixed panel, check output, limit recovery attempts, and resume without repeating paid calls.

## Decision

Use a clear Python state machine and separate provider calls. The workflow builds every context, runs a limited referee pool, safely saves each successful stage, and alone decides when the final editor may start. Do not use free-form agent handoffs or provider-hosted conversations.

## Result

Referee separation can be tested. The final editor cannot see a partial panel, and a model cannot use tools or choose the next stage. The code is explicit and provider-independent.

## Revisit if

Another workflow system can prove the same context separation, fixed-panel checks, safe writes, resume behavior, and provider boundaries.
