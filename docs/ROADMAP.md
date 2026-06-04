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
- Move feed parsing and Markdown generation out of `src/ets4/legacy.py`.
- Add typed schemas for papers, evidence, reviews, decisions, and exports.
- Add run manifests with issue date, source snapshot, model policy, cost budget,
  paper budget, human overrides, and allowed actions.
- Add unit tests for parsing, deduplication, schema validation, and Markdown rendering.

Exit criteria:

- Current RSS-to-draft behavior can run through the CLI.
- Tests pass without external network or model calls.
- `src/ets4/legacy.py` is either removed or reduced to a compatibility wrapper.

## Phase 2: Source Registry and Store

Goal: make collection reproducible and auditable.

- Implement `config/feeds.toml` loading.
- Add SQLite migrations or explicit schema initialization.
- Store source fetches, paper metadata, canonical identifiers, and raw abstracts.
- Deduplicate by DOI, arXiv id, canonical URL, and normalized title.
- Track paper lifecycle states: `candidate`, `triaged`, `rejected`, `shortlisted`, `reviewed`, `drafted`, `published`.
- Implement issue-level paper limits for triage, full review, short mention, and deep dive.
- Implement `force_include` and `force_exclude` controls.

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

Initial implementation status:

- Evidence dossiers are built from stored document pages and evidence items.
- Independent reviewer reports are stored before handling-editor reconciliation.
- The fake provider supports deterministic role-specific reports and decision memos.
- Reviewed papers are ranked into budgeted `deep_dive_draft` and
  `short_mention` selections.
- The current implementation covers relevance, methods, evidence, practitioner
  value, transferability, and handling editor roles.
- Copy editing, claim ledgers, and human override UI remain later
  implementation work.

- Implement the workflow in `docs/REVIEW_WORKFLOW.md`.
- Add role-specific reviewers: relevance, methods, evidence, practitioner value, transferability, handling editor, copy editor.
- Preserve independent reviewer reports before reconciliation.
- Add editorial budget ranking for full review, short mentions, and deep-dive drafts.
- Add strict JSON schemas for reviewer outputs.
- Add reconciliation for disagreements.
- Generate decision memos, claim ledgers, internal notes, unresolved questions, and suggested human checks.

Exit criteria:

- A paper cannot enter the public draft without passing required gates.
- Borderline and rejected papers retain explanations.
- Majority and minority reviewer views are visible in internal notes.
- The human editor can override deep-dive selections before final draft generation.
- The editor receives useful correction targets, not just polished prose.

## Phase 5: Evaluation Harness

Goal: make quality measurable before optimizing prompts or models.

Initial implementation status:

- Benchmark labels are loaded from JSON fixtures.
- `ets4 evaluate` scores completed runs against labeled paper sets.
- Evaluation runs and per-paper results are stored in SQLite.
- Current metrics cover triage accuracy, full-review selection precision/recall,
  hard-negative false positives, high-value false negatives, required evidence
  coverage, citation validity, reviewer disagreement, editorial decision
  accuracy, and deep-dive/short-mention selection accuracy.
- Draft-quality and publication-readiness metrics remain blocked until Phase 6
  draft export exists.

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

Initial implementation status:

- `ets4 export` writes an issue-level draft Markdown file and companion internal
  notes under `exports/{issue_id}/`.
- Public Markdown includes site-style front matter with `draft: true`.
- Internal notes include review metadata, panel summaries, open human-editor
  questions, reviewer reports, claim ledger, and extracted evidence.
- Generated artifacts are recorded in SQLite.
- Exports include an ETS4 checksum marker. Reruns overwrite unedited generated
  files but refuse to overwrite human-edited files unless `--force` is passed.
- Export to an external publishing repository remains a later integration step.

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

Initial implementation status:

- Run events are stored in `run_events`.
- Model/provider usage estimates are stored in `usage_records`.
- Source/model operations use retry/backoff wrappers.
- Archive bundles are written with `ets4 archive` and recorded in
  `archive_artifacts`.
- `ets4 run-scheduled` runs the scheduled draft pipeline through export and
  archive generation without publishing.
- The current scheduled runner writes local drafts and archives; creating pull
  requests in a downstream publishing repository remains a post-roadmap
  integration.

- Add run logs and review manifests.
- Add cost and token accounting.
- Add model/provider configuration.
- Add retries and backoff for source fetches and model calls.
- Add archive/export bundles for each issue.
- Add scheduled-run mode that generates drafts and review artifacts without publishing.

Exit criteria:

- A monthly issue can be reproduced from stored data.
- Review artifacts are auditable.
- Failures are explicit and recoverable.
