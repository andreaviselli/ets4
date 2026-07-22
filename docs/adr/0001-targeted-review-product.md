# ADR 0001: replace the prior digest product

Status: accepted on 2026-07-14.

## Context

The repository implemented feed collection, evidence extraction, paper triage, issue selection, benchmark evaluation, and draft digest export. The new implementation brief explicitly identifies that purpose as unrelated and obsolete for ETS4.

## Decision

Preserve commit `8d3be59` with annotated tag `archive/pre-targeted-review-2026-07-14`, implement on `codex/targeted-review-engine`, and replace active code/docs with the targeted three-stage manuscript-review engine.

## Consequences

The repository has one coherent product and CLI. Historical code and decisions remain available through Git rather than active compatibility modules. No runtime databases or exports are migrated.

## Reversal

Restore or fork from the archival tag if the digest product is needed. Do not recombine the two workflows without a new product boundary.
