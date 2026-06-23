# ETS4 Decision Log

This file records durable architectural and editorial decisions. It is not a
changelog. Add entries when a future agent or human editor would need the
rationale, consequences, or reversal conditions.

## 2026-06-23: Remove Narrow Fake-Provider Subset Tuning

Decision: Remove narrow fake-provider finance rejection terms that were derived
from individual papers in the six-paper accepted subset.

Context: The first accepted subset is useful for debugging the workflow, but it
is too small to justify paper-specific fake-provider calibration. Further
optimizing the deterministic baseline against those six labels would create a
misleading sense of accuracy and weaken the reason to add a real LLM provider
behind the measured gate.

Alternatives considered:

- Keep the tuned fake provider because it produced fewer subset mismatches.
- Add more paper-specific finance terms for the remaining residual cases.
- Remove narrow tuning and accept worse subset metrics until broader labels or
  a real provider justify more general behavior.

Consequence: The fake provider again treats explicit financial forecasting
without applied economic fit as borderline/methods-watch rather than hard
rejecting narrow paper-specific phrases. Current subset metrics are worse, but
the baseline is less overfit and better aligned with its role as a
deterministic pipeline control.

Reversal condition: Reintroduce stricter finance triage only from a broader
human-labeled benchmark or as explicit editorial policy, not from a handful of
subset examples.

## 2026-06-22: Codify the Real-Provider Adoption Gate

Decision: `ets4 evaluate --gate` and `ets4 replay-baseline --gate` now report a
real-provider readiness gate based on benchmark quality, label consistency, and
core evaluation metrics.

Context: The current fake-provider replay performs well on several metrics but
the accepted subset is still small and has unresolved label warnings. Without a
formal gate, agents could mistake a few improved metrics for permission to add
or adopt a real model provider.

Alternatives considered:

- Keep provider readiness as prose in pilot-validation docs only.
- Make failed gates cause `evaluate` to exit non-zero.
- Add an advisory gate report that can be stored, printed, or emitted as JSON.

Consequence: Provider adoption remains blocked until the benchmark has enough
coverage, no validation errors or label warnings, explicit hard negatives,
adequate full-review examples, strong recall/precision, high evidence coverage,
valid citations, no hidden disagreement, and calibrated editorial/publication
decisions. The gate is advisory so evaluation can still run and store results.

Reversal condition: If later pilot evidence shows these thresholds are too
strict, too lenient, or missing a critical quality dimension, revise the gate
thresholds and document the new acceptance policy.

## 2026-06-22: Treat Benchmark Label Inconsistencies as Warnings

Decision: `ets4 benchmark-status` now reports internally mixed accepted labels
as non-blocking warnings rather than structural errors.

Context: The first accepted subset contains useful human judgments, but some
residual replay mismatches come from mixed label axes, such as publication
selection, publication track, triage decision, and category fields pointing in
different directions. Those records should remain evaluable, but they should
not silently drive provider or prompt changes.

Alternatives considered:

- Reject any accepted benchmark file with label-axis inconsistencies.
- Ignore inconsistencies and treat all residual mismatches as model failures.
- Preserve evaluation readiness while surfacing warnings for human cleanup.

Consequence: Small pilot benchmarks can still be evaluated, and residual errors
can be separated into clear model behavior versus labels that need editorial
clarification. Future benchmark expansion should resolve warnings before using
the subset as a provider-adoption gate.

Reversal condition: If benchmark governance becomes stricter or warnings remain
unresolved in a formal release gate, promote selected warning classes to
validation errors.

## 2026-06-22: Make Practitioner/Applied Forecasting the Default Product

Decision: ETS4's default editorial product is a practitioner/applied economic
forecasting digest, not a broad curiosity feed.

Context: The first accepted benchmark subset showed that a vague
"interesting forecasting-adjacent papers" scope mixes practitioner applications,
academic methods, and general curiosity. That makes evaluation ambiguous and
risks confusing readers.

Alternatives considered:

- Broad curiosity feed optimized for social-media dissemination.
- Academic methods watch as the main product.
- Practitioner/applied forecasting digest with a secondary methods-watch lane.

Consequence: Benchmark labels now include explicit rubric fields for audience
fit, application type, economic relevance, forecasting contribution,
publication track, and social hook potential. Social hook potential is
dissemination metadata only; it should not promote weakly applied work into the
main track.

Reversal condition: A future editorial decision may create a separate curiosity
or academic-methods product, but that should be represented as a distinct
publication track or issue type rather than diluting the default product.

## 2026-06-22: Tighten the Fake Provider Around Applied Track Fit

Decision: The deterministic fake provider now treats generic financial or
time-series method papers as borderline, watchlist, or reject unless they show
explicit applied economic forecasting fit. Full deep-dive handling-editor
decisions are capped when the paper lacks both an explicit forecasting signal
and an applied economic signal.

Context: The accepted pilot subset error report showed repeated overpromotion:
the fake baseline marked financial/time-series methods and weakly applied papers
as directly relevant deep dives when human labels expected applied notes,
methods-watch treatment, human adjudication, or rejection.

Alternatives considered:

- Leave the fake provider as a loose pipeline smoke-test baseline.
- Add a real model provider before reducing known deterministic overpromotion.
- Tighten the fake baseline to encode the practitioner/applied product gate
  before provider comparison.

Consequence: Future fake-provider evaluations should be more conservative on
generic finance, trading-risk, volatility, and method-only papers. Stored pilot
metrics from earlier runs remain valid historical baselines but should not be
treated as the current deterministic baseline until a fresh run is generated.

Reversal condition: If broader accepted benchmarks show that the stricter fake
provider suppresses high-value applied forecasting papers, loosen the term
rules or move this logic into explicit, testable editorial rubric scoring.

## 2026-06-22: Compare Baselines with Replay Before Provider Changes

Decision: ETS4 should use `replay-baseline` to compare deterministic rubric,
selection, and provider-interface changes against an existing collected run
before adding or adopting a real model provider.

Context: The first accepted subset was small, and source collection/retrieval
state is local runtime data. Recollecting sources for every comparison would
mix model/prompt changes with source drift, while evaluating only the original
stored run would not measure current code.

Alternatives considered:

- Re-run the full scheduled pipeline from live sources for every comparison.
- Evaluate only already stored model outputs.
- Replay triage and review over the same stored papers and evidence, then
  evaluate the new run against the same accepted labels.

Consequence: `replay-baseline` creates a new evaluation-mode run from papers
triaged in a source run, reuses stored evidence, and can evaluate accepted
labels immediately. This keeps accepted labels as ignored local artifacts while
making deterministic baseline comparisons reproducible inside SQLite.

Reversal condition: If replayed runs diverge from real scheduled runs because
stored evidence is stale or source mix changes materially, require a fresh
pilot collection before comparing providers.

## 2026-06-22: Separate Editorial Decision from Publication Track

Decision: Handling-editor memos now include an explicit `publication_track`
separate from the editorial decision.

Context: The accepted pilot subset showed that a paper can deserve substantial
editorial attention while still belonging in an applied-note lane rather than a
main practitioner deep dive. Conversely, a watchlist or human-adjudication
decision does not necessarily mean the paper should appear in the publication.
The previous evaluation derived publication track from decision and selection
state, which overcounted method-watch/watchlist papers as publishable items and
made applied-note calibration hard to measure.

Alternatives considered:

- Keep deriving publication track from editorial decision and selection stage.
- Add more decision enum values that mix handling status and publication lane.
- Keep the editorial decision enum stable and add explicit publication-track
  metadata to the memo.

Consequence: Evaluation prefers the memo `publication_track` when present and
falls back to derived mapping for older stored runs. Deep-dive draft selection
now requires `full_deep_dive`, and short-mention selection requires
`short_mention`; watchlist and human-adjudication records do not automatically
become publication artifacts.

Reversal condition: If later human labels need more lanes, extend
`publication_track` values or add an issue type rather than folding track
semantics back into editorial decisions.

## 2026-06-22: Refresh Evidence from Stored Pages for Extraction Comparisons

Decision: ETS4 can rebuild evidence items from stored extracted document pages
with `refresh-evidence`, without refetching documents.

Context: The first accepted subset exposed required evidence kinds that were not
covered by the original generic extractor, such as scenario, judgement,
structural breaks, regime switching, Covid-19, volatility, and trading. The
source PDF/text pages were already stored in SQLite, so measuring improved
evidence rules should not require network retrieval or source recollection.

Alternatives considered:

- Re-run document retrieval for every evidence rule change.
- Leave older pilot evidence untouched and measure only future fresh runs.
- Rebuild evidence items from stored pages while preserving document and page
  records.

Consequence: Evidence-rule changes can be compared on existing ignored pilot
databases by running `ets4 refresh-evidence --run-id ...` followed by
`ets4 replay-baseline --labels ... --errors`. This keeps runtime artifacts out
of Git while making evidence coverage improvements measurable.

Reversal condition: If stored pages are incomplete, stale, or from a failed
extraction path, run fresh extraction or a new pilot instead of relying on
refresh.

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

## 2026-06-05: Treat Human Benchmark Labels as Calibration, Not Routine Production Work

Decision: Human benchmark labeling is required for validation and regression
testing, but it is not the intended per-issue production scoring workflow.

Context: The legacy prototype expected LLM agents to score and evaluate papers
directly. The current architecture keeps automated triage, review, scoring, and
ranking, but adds human-owned benchmark labels so those automated judgments can
be measured against an external editorial reference.

Alternatives considered:

- Require the human editor to label every production issue as benchmark data.
- Let agents create accepted benchmark labels from their own judgments.
- Use agents for routine scoring while keeping human labels for calibration,
  regression testing, and provider or workflow comparisons.

Consequence: In production, agents may score, triage, review, rank, and draft
papers, subject to human editorial approval before publication. Human benchmark
labels should be created periodically or when quality risk changes, such as
after prompt changes, provider changes, source-mix changes, observed drift, or
candidate workflow comparisons. Automated pipelines may run non-public stages,
but must not mark generated labels as accepted.

Reversal condition: None for accepted gold labels. The frequency and size of
human benchmark updates can change as ETS4 matures, but accepted benchmark
labels should remain externally human-owned.

## 2026-06-07: Defer Agent-Visible Casebook Until Holdout Benchmarks Exist

Decision: ETS4 may later use accepted human-labeled examples as an
agent-visible casebook, but this should wait until there is enough labeled data
to keep private holdout evaluation examples separate.

Context: A growing benchmark can serve two purposes. It can measure ETS4 against
human editorial judgment, and it can also provide past cases that help agents
resolve uncertain triage or review decisions. These uses conflict if the same
examples are both shown to agents and used as blind evaluation data.

Alternatives considered:

- Use all accepted labels only for evaluation.
- Show all accepted labels to agents as examples.
- Split accepted labels into agent-visible casebook examples and private
  holdout examples.

Consequence: The current pilot should first build the accepted benchmark and
evaluate the baseline. Casebook retrieval should be considered only after the
minimum benchmark targets are met: at least 100 labeled triage examples, 20
full-review examples, hard negatives, high-value examples, and examples with
weak or missing full text. If implemented, runs should log which prior cases
were shown to agents.

Reversal condition: If casebook retrieval creates label leakage, crowds out
source evidence, or makes decisions harder to audit, keep accepted labels as
evaluation-only artifacts.
