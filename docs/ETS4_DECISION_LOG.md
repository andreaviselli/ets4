# ETS4 Decision Log

This file records durable architectural and editorial decisions. It is not a
changelog. Add entries when a future agent or human editor would need the
rationale, consequences, or reversal conditions.

## 2026-06-05: Treat Phase 7 Completion as a Validation Gate, Not Production

Decision: Completing the seven implementation phases does not make ETS4
production-ready.

Context: ETS4 can collect, triage, extract evidence, review, evaluate, export,
archive, and run scheduled drafts. However, review quality has not yet been
validated against a human-labeled benchmark.

Alternatives considered:

- Start website integration immediately.
- Add a real model provider immediately.
- Run pilot validation before production or provider escalation.

Consequence: The active milestone is pilot validation. Website integration and
real provider work remain gated by benchmark results and human editorial review.

Reversal condition: ETS4 has at least one accepted benchmark, evaluation results
show no critical unsupported-claim or hard-negative failures, and the human
editor explicitly approves moving to integration or real-provider work.

## 2026-06-05: Keep Fake Provider as the Baseline

Decision: The fake provider remains the default baseline until a human benchmark
exists.

Context: The fake provider is deterministic, offline, cheap, and testable. It is
not intended to produce SOTA editorial prose, but it gives stable outputs for
pipeline validation.

Alternatives considered:

- Add OpenAI or another real model provider before benchmark labeling.
- Tune prompts or model behavior based on subjective inspection only.

Consequence: Real providers should be compared against the fake-provider
baseline on the same accepted benchmark before adoption.

Reversal condition: A human benchmark exists and a candidate provider improves
target metrics without unacceptable regressions in unsupported claims, hard
negative precision, evidence citation validity, cost, or disagreement handling.

## 2026-06-05: Require Evidence Before Review

Decision: Full review should be grounded in stored evidence items, not only
abstracts or model impressions.

Context: Pilot runs showed that HTML pages and weak retrieval can produce
boilerplate evidence if not guarded. This risks polished but unsupported draft
claims.

Alternatives considered:

- Let review proceed from whatever text retrieval returns.
- Fall back silently to abstract-only review.
- Fail weak evidence explicitly and record the failure.

Consequence: The document processor now applies extraction quality checks.
Weak, boilerplate-heavy, or insufficient evidence extraction is stored as an
explicit document/review limitation.

Reversal condition: A future review mode may allow abstract-only triage or
watchlist decisions, but public deep-dive drafts should still require adequate
full-text evidence.

## 2026-06-05: Generate Benchmark Templates, Do Not Generate Gold Labels

Decision: ETS4 may generate editable benchmark templates from a run, but accepted
gold labels must be created by human editorial review.

Context: The pilot validation roadmap requires a benchmark before real-provider
work. A tool is useful to collect paper metadata and system context, but model
or system defaults should not become accepted labels automatically.

Alternatives considered:

- Handwrite benchmark JSON from scratch.
- Let ETS4 infer accepted labels from its own decisions.
- Generate draft labels and require explicit human acceptance.

Consequence: `ets4 benchmark-template` writes draft labels with
`label_status: "needs_human_label"`. `ets4 evaluate` refuses those labels until
they are marked `accepted`.

Reversal condition: None for gold labels. Models may suggest labels, but
accepted labels should remain human-owned.

## 2026-06-05: Keep Runtime Outputs Out of Git

Decision: SQLite databases, exports, benchmark templates under `exports/`, local
feed configs, archives, and secrets are runtime artifacts and should stay out of
version control.

Context: Pilot runs generate databases, draft pages, archives, and benchmark
templates. These can grow quickly and may contain local state or unpublished
editorial work.

Alternatives considered:

- Commit pilot databases and generated drafts for reproducibility.
- Keep source-controlled code and docs only, while archives remain local.

Consequence: `data/`, `exports/`, local SQLite files, `config/feeds.toml`, and
`.env` remain ignored. Reproducibility should come from manifests, source code,
and explicit archive artifacts when intentionally shared.

Reversal condition: A specific small fixture may be committed under `tests/` if
it is curated, stable, non-sensitive, and needed for automated testing.

## 2026-06-05: Publication Must Remain Human-Approved

Decision: ETS4 should generate draft artifacts, not publish autonomously.

Context: ETS4 is an editorial review assistant. Human review is required for
paper selection, final claims, corrections, and website publication.

Alternatives considered:

- Automatically commit or publish generated drafts to the website repository.
- Create local drafts or draft pull requests that require explicit approval.

Consequence: Website integration is gated by pilot validation and should start
with draft artifacts or draft pull requests only.

Reversal condition: Do not reverse for public publication. Automation can be
expanded for scheduling and draft preparation, but final publication should
remain manually approved.
