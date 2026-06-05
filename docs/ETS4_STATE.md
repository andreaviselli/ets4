# ETS4 State

Last updated: 2026-06-05

This file is the fast handoff note for future ETS4 work. Read it after the
README and before making implementation changes.

## Current Status

ETS4 has completed the seven implementation phases in `docs/ROADMAP.md` and is
now in post-roadmap pilot validation.

The active milestone is `docs/PILOT_VALIDATION.md`: validate the system on real
sources, create a human-labeled benchmark, evaluate the fake-provider baseline,
and decide whether the next investment should be retrieval, review providers,
benchmark expansion, or website integration.

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
- `ets4 evaluate` rejects draft benchmark labels unless each label is marked
  `label_status: "accepted"`.

## Current Pilot Position

We are after the first real pilot run and after the first retrieval-quality
correction loop. We are before the first human-labeled benchmark evaluation.

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
- accepted benchmark labels: 0

The remaining `403 Forbidden` failure is explicit and recoverable. It should not
block benchmark labeling unless that source is editorially important.

## Next Recommended Task

Create the first accepted human benchmark from the generated template.

Suggested scope:

- label a small initial subset before trying to label all 21 papers
- include at least one deep-dive candidate, one short mention, one rejected or
  weak candidate, and the blocked-full-text failure if useful
- fill `relevance_label`, expected triage/editorial decisions, deep-dive and
  short-mention expectations, required evidence kinds, `hard_negative`, and
  `high_value`
- set `label_status` to `accepted` only after human inspection
- run `ets4 evaluate` against the accepted benchmark

Suggested command pattern:

```bash
ets4 benchmark-template --run-id run-960b75015cc3
ets4 evaluate --run-id run-960b75015cc3 --labels path/to/accepted-benchmark.json
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
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json
ets4 export --run-id run-example123
ets4 archive --run-id run-example123
ets4 run-scheduled --issue-date YYYY-MM-DD
```

## Known Gaps

- No real model provider is implemented yet.
- No accepted human benchmark exists yet.
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
