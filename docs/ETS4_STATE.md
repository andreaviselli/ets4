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
  review, and handling-editor decisions.
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
- triage decision accuracy: 0.3333
- triage category accuracy: 0.3333
- selected-paper precision: 0.6
- relevant-paper recall: 1.0
- hard-negative false-positive rate: 0.0
- required evidence-kind coverage: 0.3611
- papers missing required evidence: 3
- reviewer citation coverage: 1.0
- invalid citation rate: 0.0
- editorial decision accuracy: 0.0
- deep-dive selection accuracy: 0.5
- short-mention selection accuracy: 0.8333
- publication-track accuracy: 0.1667
- publication-track distribution: 1 applied note, 1 methods watch, 4 rejects

Interpretation: the fake-provider baseline preserves citation validity on the
accepted subset, but it does not match human editorial labels well enough for
real use. Under the practitioner/applied rubric it promotes too many papers into
deep-dive-like treatment, especially methods/curiosity papers that should be
short applied notes, methods watch, or rejects. The next implementation work
should make benchmark inspection and error analysis easier before adding a real
provider.

## Next Recommended Task

Implement benchmark evaluation reporting and error analysis for the accepted
subset.

Suggested scope:

- add a CLI/report command or evaluation option that lists per-paper mismatches
  between human labels and system outputs
- show which papers drive low triage accuracy, editorial decision accuracy, and
  evidence-kind coverage
- keep accepted human labels as ignored local artifacts unless a curated test
  fixture is intentionally created
- update docs after the reporting workflow is implemented

Suggested command pattern:

```bash
ets4 evaluate \
  --run-id run-960b75015cc3 \
  --labels exports/benchmarks/run-960b75015cc3.initial-subset.json \
  --json
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
