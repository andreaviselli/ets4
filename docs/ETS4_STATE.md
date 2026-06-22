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
- The fake model provider is the deterministic baseline for triage, panel
  review, and handling-editor decisions. It now distinguishes applied economic
  forecasting signals from generic financial/time-series methods and caps
  full-deep-dive decisions when applied forecasting fit is limited.
- Exports write draft Markdown and internal notes under ignored `exports/`.
- Archive bundles and run events are implemented for reproducibility.
- `ets4 benchmark-template` creates human-editable benchmark JSON from a
  completed run.
- `ets4 benchmark-status` validates benchmark JSON, reports draft or incomplete
  labels, and can write a smaller copied subset for human editing without
  accepting or inventing labels.
- `ets4 evaluate` rejects draft benchmark labels unless each label is marked
  `label_status: "accepted"`.
- Benchmark labels now include practitioner/applied rubric fields: audience
  fit, application type, economic relevance, forecasting contribution,
  publication track, and social hook potential.
- `ets4 evaluate --errors` reports per-paper mismatches between accepted human
  labels and ETS4 outputs for triage, category, editorial decisions, selection,
  publication track, and required evidence coverage. `--json` includes the same
  report in a `mismatches` array.
- `ets4 replay-baseline` creates a new evaluation-mode run from papers triaged
  in an existing source run, reuses stored evidence, and can evaluate accepted
  labels immediately. This supports deterministic baseline comparison without
  recollecting sources.

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
- latest deterministic replay run: `run-871a316d887d`
- latest replay evaluation run: `eval-5330c084189437a2`
- replay triaged papers: 21
- replay selected for full review: 7
- replay reviewed papers: 7
- replay review errors: 0
- replay triage decision accuracy: 0.8333
- replay selected-paper precision: 0.75
- replay relevant-paper recall: 0.75
- replay required evidence-kind coverage: 0.3611
- replay editorial decision accuracy: 0.1667
- replay deep-dive selection accuracy: 0.8333
- replay publication-track accuracy: 0.3333
- replay per-paper mismatches: 18

Interpretation: the fake-provider baseline preserves citation validity on the
accepted subset. The replayed baseline improved triage decision accuracy,
deep-dive selection accuracy, publication-track accuracy, and total mismatch
count compared with the stored pilot evaluation. Remaining failures now
concentrate in publication-track/editorial calibration, short-mention
selection, missing review outputs for rejected or unselected papers, and
evidence-kind extraction gaps. The current result is still not strong enough for
real-provider adoption or website integration.

## Next Recommended Task

Improve publication-track and editorial calibration for the practitioner/applied
digest before adding a real provider.

Suggested scope:

- separate `methods_watch`/watchlist records from publishable applied notes in
  evaluation and selection
- make scenario/evaluation papers route toward applied notes unless they have a
  direct forecasting contribution
- preserve or improve the latest replay metrics on the accepted subset
- keep accepted human labels as ignored local artifacts unless a curated test
  fixture is intentionally created
- do not add a real model provider until editorial/publication-track accuracy
  improves on accepted labels

Suggested command pattern:

```bash
ets4 replay-baseline \
  --source-run-id run-960b75015cc3 \
  --labels exports/benchmarks/run-960b75015cc3.initial-subset.json \
  --errors
```

## Working Commands

```bash
ets4 init-db
ets4 manifest --issue-date YYYY-MM-DD
ets4 collect --run-id run-example123
ets4 triage --run-id run-example123
ets4 select --run-id run-example123
ets4 extract --run-id run-example123
ets4 review --run-id run-example123
ets4 benchmark-template --run-id run-example123
ets4 benchmark-status --labels path/to/benchmark.json
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json
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
