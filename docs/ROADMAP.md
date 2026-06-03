# ETS4 Roadmap

## Milestone 1: Repository Baseline

- Initialize this directory as an independent Git repository.
- Add packaging metadata and dependency declarations.
- Keep secrets out of version control.
- Document the intended relationship with the website repository.

## Milestone 2: Pipeline Stabilization

- Move notebook logic into importable Python modules.
- Preserve the current `get_ets4` interface while introducing a CLI.
- Add structured configuration for feeds, models, thresholds, and output paths.
- Add smoke tests for feed parsing, JSON validation, deduplication, and Markdown export.

## Milestone 3: Editorial Store

- Add a SQLite database for papers, sources, review runs, and publication state.
- Store model outputs as structured JSON.
- Track paper status across issues: candidate, shortlisted, rejected, deep-dive, drafted, published.

## Milestone 4: Review Workflow

- Implement staged review: triage, full-text review, methodological critique, practitioner relevance, final editor pass.
- Add disagreement handling and confidence flags.
- Produce internal review notes alongside public drafts.

## Milestone 5: Evaluation

- Build a labeled validation set from past candidate papers.
- Measure relevance precision/recall and scoring consistency.
- Compare prompts and models before adopting changes.
- Track known failure modes.

## Milestone 6: Website Draft Export

- Generate Markdown matching the publishing site's front matter and page conventions.
- Export draft pages to a configured website repository.
- Keep exported pages in draft mode until human approval.
