# ETS4 State

Last updated: 2026-06-22

This file is the fast handoff note for future ETS4 work. Read it after the
README and before making implementation changes.

## Current Status

ETS4 has completed the seven implementation phases in `docs/ROADMAP.md` and is
now in post-roadmap pilot validation.

The active milestone is `docs/PILOT_VALIDATION.md`: validate the system on real
sources, evaluate accepted practitioner/applied forecasting labels, and decide
whether the next investment should be retrieval, review providers, benchmark
expansion, or website integration.

## Latest Implementation State

- Package skeleton, CLI, config loading, run manifests, and SQLite schema exist.
- Source registry and RSS collection are implemented.
- Deduplication covers DOI, arXiv id, canonical URL, normalized title, and fuzzy
  title matching.
- Budgeted candidate selection exists for full review, deep-dive drafts, and
  short mentions.
- Evidence extraction supports local text, local PDFs, remote PDFs, arXiv
  abstract-page to PDF resolution, and HTML landing-page PDF discovery.
- Evidence quality gates reject weak extraction and HTML boilerplate before
  review.
- Evidence extraction now includes domain-specific benchmark kinds for
  scenarios, judgement, structural breaks, Covid-19, volatility, and trading in
  addition to the generic method/dataset/metric/baseline/code/limitation kinds.
- The fake model provider is the deterministic baseline for triage, panel
  review, and handling-editor decisions. It now distinguishes applied economic
  forecasting signals from generic financial/time-series methods and caps
  full-deep-dive decisions when applied forecasting fit is limited.
- Exports write draft Markdown and internal notes under ignored `exports/`.
- Archive bundles and run events are implemented for reproducibility.
- `ets4 benchmark-template` creates human-editable benchmark JSON from a
  completed run.
- `ets4 benchmark-status` validates benchmark JSON, reports draft or incomplete
  labels, emits accepted-label consistency warnings with human-resolution
  suggestions, reports coverage against pilot benchmark targets, can print the
  audit as JSON, and can write a smaller copied subset for human editing
  without accepting or inventing labels.
- `ets4 evaluate` rejects draft benchmark labels unless each label is marked
  `label_status: "accepted"`.
- Benchmark labels now include practitioner/applied rubric fields: audience
  fit, application type, economic relevance, forecasting contribution,
  publication track, and social hook potential.
- `ets4 evaluate --errors` reports per-paper mismatches between accepted human
  labels and ETS4 outputs for triage, category, editorial decisions, selection,
  publication track, and required evidence coverage. `--json` includes the same
  report in a `mismatches` array.
- `ets4 evaluate --gate` and `ets4 replay-baseline --gate` report whether the
  current benchmark/evaluation satisfies the real-provider adoption gate. Gate
  failures are advisory output, not evaluation command failures.
- `ets4 replay-baseline` creates a new evaluation-mode run from papers triaged
  in an existing source run, reuses stored evidence, and can evaluate accepted
  labels immediately. This supports deterministic baseline comparison without
  recollecting sources.
- `ets4 refresh-evidence` rebuilds evidence items from stored extracted pages
  without refetching documents. Use it after evidence-kind rule changes before
  replaying a baseline.

## Current Pilot Position

We are after the first real pilot run, after the first retrieval-quality
correction loop, and after the first small human-labeled benchmark evaluation.

The last real pilot run used:

- run id: `run-960b75015cc3`
- issue date: `2026-06-05`
- database: ignored local runtime SQLite under `data/`
- benchmark template: ignored local JSON under `exports/benchmarks/`

Observed pilot outcome after retrieval improvements:

- collected candidates: 21
- selected for full review: 10
- usable PDF-backed reviewed papers: 9
- remaining document failure: one `403 Forbidden` repository response
- generated benchmark template papers: 21
- accepted initial-subset benchmark labels: 6

The remaining `403 Forbidden` failure is explicit and recoverable. It should not
block benchmark labeling unless that source is editorially important.

## Latest Evaluation

The first accepted benchmark subset was evaluated on 2026-06-22 and revised
under the practitioner/applied forecasting rubric.

- labels file: `exports/benchmarks/run-960b75015cc3.initial-subset.json`
- benchmark version: `run-960b75015cc3-human-v1-subset`
- labeled papers: 6
- triage decision accuracy: 0.5
- triage category accuracy: 0.6667
- selected-paper precision: 0.8
- relevant-paper recall: 1.0
- hard-negative false-positive rate: 0.0
- required evidence-kind coverage: 0.3611
- papers missing required evidence: 3
- reviewer citation coverage: 1.0
- invalid citation rate: 0.0
- editorial decision accuracy: 0.1667
- deep-dive selection accuracy: 0.3333
- short-mention selection accuracy: 0.8333
- publication-track accuracy: 0.1667
- publication-track distribution: 2 applied notes, 4 rejects
- latest evidence refresh: 9 documents refreshed, 3196 evidence items, 0 skips
- benchmark-status warnings: 3 across 2 papers
- benchmark coverage: 6/100 accepted labels, 3/20 full-review examples,
  hard-negative/directly-relevant/transferable-method/weak-full-text coverage
  targets met
- latest deterministic replay run: `run-d89f0363fdd3`
- latest replay evaluation run: `eval-c8a246642d17ab57`
- replay triaged papers: 21
- replay selected for full review: 9
- replay reviewed papers: 9
- replay review errors: 1
- replay triage decision accuracy: 0.6667
- replay triage category accuracy: 0.6667
- replay selected-paper precision: 0.8
- replay relevant-paper recall: 1.0
- replay required evidence-kind coverage: 1.0
- replay editorial decision accuracy: 0.6667
- replay deep-dive selection accuracy: 0.8333
- replay short-mention selection accuracy: 1.0
- replay publication-track accuracy: 0.8333
- replay per-paper mismatches: 8
- provider gate status: not ready
- provider gate failed checks: 4
- provider gate blockers: benchmark warnings, 6/100 labeled papers, 3/20
  full-review examples, editorial decision accuracy 0.6667/0.8

Interpretation: the fake-provider baseline preserves citation validity on the
accepted subset. After auditing overfitting risk, the fake provider no longer
uses narrow rejection terms derived from individual accepted-subset papers. The
less-tailored replay keeps evidence coverage, citation validity,
hard-negative precision, and relevant recall strong, but it regresses
triage/editorial accuracy on the tiny accepted subset. That is the preferred
tradeoff: the fake provider should remain a stable conservative pipeline
baseline, not a rule set optimized for a handful of labels. Evidence-kind
coverage is now complete on the accepted subset after refreshing stored pages.
The current result is still too small and label-warning-bound for real-provider
adoption or website integration.

## Next Recommended Task

Resolve the accepted-label warning cases and expand the benchmark before adding
a real provider. The provider gate now makes this explicit.

Suggested scope:

- resolve accepted-label warnings where editorial decision, publication track,
  category, or selection fields point in different directions
- use `ets4 benchmark-status --json --labels ...` to inspect the exact warning
  records and coverage gaps before changing ignored local labels
- expand the accepted benchmark by at least 94 triage labels and 17 full-review
  labels to reach the documented minimum provider-gate coverage target
- preserve hard-negative false-positive rate 0, evidence coverage 1.0, and
  citation validity on the accepted subset
- keep accepted human labels as ignored local artifacts unless a curated test
  fixture is intentionally created
- do not add a real model provider until evidence coverage and editorial
  accuracy improve on accepted labels

Suggested command pattern:

```bash
ets4 refresh-evidence --run-id run-960b75015cc3
ets4 replay-baseline \
  --source-run-id run-960b75015cc3 \
  --labels exports/benchmarks/run-960b75015cc3.initial-subset.json \
  --errors \
  --gate
```

## Working Commands

```bash
ets4 init-db
ets4 manifest --issue-date YYYY-MM-DD
ets4 collect --run-id run-example123
ets4 triage --run-id run-example123
ets4 select --run-id run-example123
ets4 extract --run-id run-example123
ets4 refresh-evidence --run-id run-example123
ets4 review --run-id run-example123
ets4 benchmark-template --run-id run-example123
ets4 benchmark-status --labels path/to/benchmark.json
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json --gate
ets4 export --run-id run-example123
ets4 archive --run-id run-example123
ets4 run-scheduled --issue-date YYYY-MM-DD
```

## Known Gaps

- No real model provider is implemented yet.
- A small accepted human benchmark subset exists locally, but no source-controlled
  benchmark fixture has been curated from it.
- No website-repository integration exists yet.
- Human override workflow exists conceptually and through config controls, but
  there is no dedicated interactive UI.
- Draft quality and publication-readiness evaluation need real human labels.
- Blocked repository retrieval may need source-specific fallback policy.

## Quality Gate Before Committing

Run:

```bash
python -m pytest
python -m ruff check src tests
python -m py_compile src/ets4/*.py src/ets4/store/*.py src/ets4/collect/*.py src/ets4/documents/*.py src/ets4/review/*.py src/ets4/evaluate/*.py src/ets4/export/*.py src/ets4/ops/*.py
```
