# Pilot Validation

The seven-phase roadmap created a working ETS4 system. The next milestone is
not another feature phase. It is a validation gate that decides whether ETS4 is
reliable enough for real model providers, scheduled use, and downstream website
integration.

## Purpose

The pilot should answer four questions:

1. Does ETS4 retrieve and triage the right papers from real sources?
2. Does the evidence extraction layer provide enough support for editorial
   review?
3. Does the review workflow produce useful correction targets for a human
   editor?
4. Do stronger model providers improve measurable quality without increasing
   unsupported claims, false positives, or cost beyond the editorial budget?

Until those questions are answered, ETS4 should remain a draft-generation and
review-assistance system, not a production publishing system.

## Scope

The pilot should use the current CLI and SQLite workflow.

In scope:

- real source collection from configured feeds
- human inspection of collected papers and selected papers
- benchmark label creation
- evaluation of fake-provider outputs
- later evaluation of a real model provider against the same benchmark
- draft export to local `exports/`
- archive creation for reproducibility

Out of scope:

- autonomous publication
- automatic commits to the publishing repository
- website pull requests before the review quality is measured
- replacing human editorial judgment
- optimizing prose style before evidence quality is validated

## Pilot Run Protocol

Run one or more real pilot issues using the scheduled draft workflow:

```bash
ets4 init-db
ets4 run-scheduled --issue-date YYYY-MM-DD
```

For each pilot issue, inspect:

- `run_events` for stage completion and failures
- `source_events` for source-level collection failures
- `documents` and `document_events` for full-text retrieval failures
- `evidence_items` for coverage and source-locator quality
- `reviewer_reports` for role-specific usefulness
- `editorial_decisions` for overconfidence or hidden disagreement
- exported `issue.md` and `internal-notes.md`
- archive zip contents

The human editor should record notes about false positives, false negatives,
weak evidence, missing evidence, misleading draft claims, and useful reviewer
questions.

## Benchmark Creation

The first real benchmark should be manually labeled. Models may suggest labels,
but accepted labels must come from human editorial review.

Create the editable benchmark template from a completed pilot run:

```bash
ets4 benchmark-template --run-id run-example123
```

The command writes an ignored draft JSON file under `exports/benchmarks/` by
default. Each paper starts with `label_status: "needs_human_label"` and blank
gold-label fields. The human editor should inspect the exported issue,
internal notes, source paper, and evidence context, then set reviewed labels to
`accepted`. ETS4 refuses to evaluate unaccepted draft labels.

Minimum initial target:

- 100 triage examples
- 20 full-review examples
- explicit hard negatives
- examples of directly relevant papers
- examples of transferable non-economic methods
- examples with weak or missing full text

The benchmark should use the JSON format described in `docs/EVALUATION.md`.

Recommended labels:

- `relevance_label`
- `expected_category`
- `expected_triage_decision`
- `expected_editorial_decision`
- `expected_deep_dive`
- `expected_short_mention`
- `required_evidence_kinds`
- `hard_negative`
- `high_value`

## Evaluation Protocol

After a pilot run and benchmark labeling:

```bash
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json
```

Track at least:

- triage decision accuracy
- selected-paper precision
- relevant-paper recall
- hard-negative false-positive rate
- high-value false-negative count
- required evidence-kind coverage
- citation coverage
- invalid citation rate
- reviewer disagreement
- editorial decision accuracy
- deep-dive selection accuracy

The system should not progress to real-model production use if it fails on hard
negatives, produces unsupported draft claims, hides reviewer disagreement, or
selects papers without adequate evidence.

## Real Model Provider Gate

A real provider, such as an OpenAI provider, should be added only after the
first human benchmark exists.

The provider should sit behind the existing model-provider interface and must
write:

- provider name
- model name
- prompt version
- structured outputs
- token usage
- estimated cost
- validation errors

Before adoption, compare the real provider against the fake-provider baseline on
the same benchmark.

Accept a real provider only if it improves the target metrics without
unacceptable regressions in:

- unsupported claim rate
- hard-negative precision
- evidence citation validity
- cost
- reviewer disagreement handling

## Website Integration Gate

Connecting ETS4 to the publishing repository should happen only after pilot
validation.

The first integration should create local draft artifacts or a draft pull
request. It must not publish automatically.

Minimum requirements before website integration:

- at least one completed pilot issue
- benchmark evaluation results stored in SQLite
- human review of exported draft and internal notes
- no known critical unsupported-claim failure
- explicit human approval step before publication

## Exit Criteria

The pilot milestone is complete when:

- a real pilot issue can be reproduced from SQLite and archive artifacts
- the first benchmark exists and is usable with `ets4 evaluate`
- the human editor has reviewed exported drafts and internal notes
- failure modes are documented
- a decision is made on whether to add a real model provider, improve retrieval,
  expand benchmark labels, or integrate with the website repository

## Recommended Next Decision

After the pilot, choose one of these paths:

- **Improve retrieval** if too many selected papers lack usable full text.
- **Improve review prompts/providers** if evidence is adequate but reviewer
  reports are weak.
- **Expand benchmark coverage** if the metrics are too sparse to guide model
  changes.
- **Integrate with the website repository** if review quality is acceptable and
  the human editor wants a draft pull-request workflow.
