# ETS4 Architecture

ETS4 should be treated as the editorial engine. The website repository should
remain the publishing surface.

## Boundaries

- `ets4`: collection, review, evaluation, draft generation.
- `andreaviselli.github.io`: final site rendering and publication.

ETS4 may write draft Markdown into the website repository, but it should not
publish pages directly without human review.

## Target Workflow

1. Collect candidate papers from configured sources.
2. Normalize and deduplicate metadata.
3. Store raw records and review outputs.
4. Run staged editorial review.
5. Generate draft page and internal review notes.
6. Export the draft to the website repo with `draft: true`.
7. Apply human comments and corrections.
8. Publish only after explicit approval.

## Future Components

- `collect`: source ingestion and metadata normalization.
- `store`: SQLite-backed paper and review database.
- `review`: multi-stage editorial review workflow.
- `deepdive`: grounded full-paper analysis.
- `evaluate`: benchmark suite for reviewer quality.
- `export`: website-compatible draft generation.

## Design Principle

The project should optimize for editorial reliability, not raw automation. The
model should help discover, inspect, summarize, and critique papers, while the
final publication decision remains human.

