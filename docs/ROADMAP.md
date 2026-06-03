# ETS4 Roadmap

This roadmap intentionally prioritizes review quality and evaluation over a
larger interface. A dashboard or web app should wait until the editorial core is
measurably reliable.

## Phase 0: Repository Reset

Goal: remove prototype clutter and define the target system.

- Keep only the active prototype, project metadata, and design docs.
- Remove deprecated notebooks and generated outputs from version control.
- Add `config/`, `data/`, and `exports/` as the working structure.
- Document the review workflow and evaluation standard.

Exit criteria:

- Repository contains no local machine paths.
- Runtime/generated files are ignored.
- Architecture, review workflow, and evaluation contracts are explicit.

## Phase 1: Package and CLI

Goal: migrate from a single script to a maintainable Python package.

- Create `src/ets4/` package.
- Add CLI commands:
  - `ets4 collect`
  - `ets4 triage`
  - `ets4 review`
  - `ets4 evaluate`
  - `ets4 export`
- Move feed parsing and Markdown generation out of `ets4.py`.
- Add typed schemas for papers, evidence, reviews, decisions, and exports.
- Add unit tests for parsing, deduplication, schema validation, and Markdown rendering.

Exit criteria:

- Current RSS-to-draft behavior can run through the CLI.
- Tests pass without external network or model calls.
- `ets4.py` is either removed or reduced to a compatibility wrapper.

## Phase 2: Source Registry and Store

Goal: make collection reproducible and auditable.

- Implement `config/feeds.toml` loading.
- Add SQLite migrations or explicit schema initialization.
- Store source fetches, paper metadata, canonical identifiers, and raw abstracts.
- Deduplicate by DOI, arXiv id, canonical URL, and normalized title.
- Track paper lifecycle states: `candidate`, `triaged`, `rejected`, `shortlisted`, `reviewed`, `drafted`, `published`.

Exit criteria:

- Re-running collection does not create duplicate papers.
- Every paper can be traced to a source event.
- Review state survives across runs.

## Phase 3: Evidence Extraction

Goal: stop asking the model to review papers from weak context.

- Fetch full text for shortlisted candidates.
- Preserve PDF page numbers and source locators.
- Extract abstracts, methods, datasets, tables, figures, metrics, baselines, code links, and limitations.
- Store evidence items separately from model prose.
- Add failure handling for paywalls, broken PDFs, and malformed feeds.

Exit criteria:

- Every full review cites evidence items.
- Missing full text produces an explicit review limitation.
- Draft summaries avoid claims without supporting evidence.

## Phase 4: Review Workflow

Goal: replace one-shot scoring with staged editorial judgment.

- Implement the workflow in `docs/REVIEW_WORKFLOW.md`.
- Add role-specific reviewers: relevance, methods, evidence, practitioner value, editor.
- Add strict JSON schemas for reviewer outputs.
- Add reconciliation for disagreements.
- Generate internal notes containing confidence, unresolved questions, and suggested human checks.

Exit criteria:

- A paper cannot enter the public draft without passing required gates.
- Borderline and rejected papers retain explanations.
- The editor receives useful correction targets, not just polished prose.

## Phase 5: Evaluation Harness

Goal: make quality measurable before optimizing prompts or models.

- Implement the benchmark described in `docs/EVALUATION.md`.
- Create labeled paper sets for relevance, category, evidence support, and publication readiness.
- Add regression tests for prompts, models, and retrieval changes.
- Track false positives, false negatives, unsupported claims, and calibration drift.

Exit criteria:

- Any review-system change can be compared against the current baseline.
- Prompt/model changes require benchmark results.
- Known failure modes are tracked and tested.

## Phase 6: Draft Export

Goal: produce publication-ready drafts without bypassing human review.

- Export Markdown with site-compatible front matter.
- Export companion internal notes.
- Keep `draft: true` by default.
- Make exports idempotent.
- Refuse to overwrite manually edited drafts unless explicitly requested.

Exit criteria:

- A complete issue can be exported to `exports/`.
- A configured publishing repository can receive draft files.
- Publication remains a manual approval step.

## Phase 7: Operational Hardening

Goal: make the tool dependable for monthly use.

- Add run logs and review manifests.
- Add cost and token accounting.
- Add model/provider configuration.
- Add retries and backoff for source fetches and model calls.
- Add archive/export bundles for each issue.

Exit criteria:

- A monthly issue can be reproduced from stored data.
- Review artifacts are auditable.
- Failures are explicit and recoverable.
