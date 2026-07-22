# ADR 0001: replace the old digest product

Status: accepted on 2026-07-14.

## Context

The repository used to collect feeds, extract papers, sort them, evaluate selections, and export a digest. The new brief says this purpose is unrelated and should be replaced.

## Decision

Protect commit `8d3be59` with tag `archive/pre-targeted-review-2026-07-14`. Build the three-stage manuscript-review tool on `codex/targeted-review-engine` and replace the active code and docs.

## Result

The repository has one clear product and command-line tool. The old code remains in Git history. No old database or export is moved into the new system.

## Revisit if

The digest is needed again. Restore or fork it from the archive tag; do not mix both workflows into ETS4 without a new product boundary.
