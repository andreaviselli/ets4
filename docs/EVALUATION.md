# Evaluation

ETS4 should treat evaluation as a production requirement. A review system that
cannot be measured will drift toward polished but unreliable prose.

## Evaluation Goals

The system should be evaluated for:

- relevance selection quality
- category accuracy
- evidence support
- scoring calibration
- editorial budget selection quality
- reviewer disagreement handling
- draft usefulness for human editing
- regression stability across prompt/model changes

## Benchmark Sets

Create small, high-quality labeled sets before scaling.

ETS4 currently supports JSON benchmark files with this shape:

```json
{
  "version": "benchmark-id",
  "papers": [
    {
      "paper_id": "paper-1",
      "relevance_label": "directly_relevant",
      "audience_fit": "practitioner",
      "application_type": "forecasting",
      "economic_relevance": "high",
      "forecasting_contribution": "genuine_application",
      "publication_track": "deep_dive",
      "social_hook_potential": "medium",
      "expected_category": "directly_relevant",
      "expected_triage_decision": "assign_reviewers",
      "expected_editorial_decision": "full_deep_dive",
      "expected_deep_dive": true,
      "expected_short_mention": false,
      "required_evidence_kinds": ["method", "dataset", "metric"],
      "hard_negative": false,
      "high_value": true
    }
  ]
}
```

To create the first editable benchmark from a completed pilot run:

```bash
ets4 benchmark-template --run-id run-example123
```

The template is written under `exports/benchmarks/` unless `--output` is
provided. It includes paper metadata, system triage/review context, selection
state, evidence availability, and blank human-label fields. Draft templates set
`label_status` to `needs_human_label`; `ets4 evaluate` rejects those files until
the human editor changes reviewed labels to `accepted`.

To inspect labeling progress without treating draft labels as gold labels:

```bash
ets4 benchmark-status --labels exports/benchmarks/run-example123.benchmark-template.json
```

The status command validates benchmark JSON, reports labels that are still draft
or incomplete, and exits non-zero only for structural validation errors. To make
a smaller human-editing file from a generated template:

```bash
ets4 benchmark-status \
  --labels exports/benchmarks/run-example123.benchmark-template.json \
  --subset-output exports/benchmarks/run-example123.initial-subset.json \
  --subset-size 6
```

Subset files copy existing paper records and preserve draft label fields. They
do not infer labels or mark labels as accepted.

Run evaluation with:

```bash
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json
```

Each evaluation stores one row in `evaluation_runs` and one row per paper in
`evaluation_items`.

To inspect the failures behind aggregate scores, add `--errors`:

```bash
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json --errors
```

The error report lists each labeled paper with mismatches between human labels
and ETS4 outputs for triage decision, category, editorial decision, deep-dive
selection, short-mention selection, publication track, and missing required
evidence kinds. Each mismatch includes the paper title, paper id, accepted human
label, system output, deterministic failure type, and a concise failure reason.

The same output starts with an error summary that groups mismatches by report
field, failure type, and missing required evidence kind. It also prints short
recommended next actions derived from the observed failure types, such as
tightening desk screening, making publication-track gates more conservative, or
improving evidence-kind extraction.

For machine-readable inspection, `--json` includes a `mismatches` array with the
same per-paper fields and an `error_summary` object with the grouped counts.

## Labeling Guide

Use benchmark labels to describe the human editor's expected judgment, not the
system's current output. System context in a benchmark template is useful
evidence for labeling, but it should not be copied blindly into gold labels.

ETS4's default editorial product is a practitioner/applied forecasting digest.
The core question is not "is this paper interesting?" It is:

> Does this paper help someone forecast, nowcast, evaluate forecasts, monitor
> risk, stress-test scenarios, or make decisions in an economic, financial,
> policy, energy, business, or market setting?

Academic novelty and social-media curiosity are secondary. They can justify a
`methods_watch` or a hook for dissemination, but they should not turn a weakly
applied paper into a main recommendation.

Set `label_status` to `accepted` only after human inspection. Leave it as
`needs_human_label` while a label is draft, incomplete, or only model-suggested.

### `human_notes`

Use this for the short reason behind the label. It should be enough for a future
editor to understand the decision without reopening every artifact.

Examples:

- `Direct forecasting paper with macroeconomic target variables and usable full-text evidence.`
- `Causal macro paper; useful context but not a forecasting contribution.`
- `Promising method, but fit to economic forecasting is unclear without human review.`

### `relevance_label`

Allowed values:

- `directly_relevant`: The paper directly studies economic or financial
  forecasting, forecast evaluation, predictive uncertainty, nowcasting, scenario
  forecasting, or closely related time-series prediction.
- `paper_of_interest`: The paper is not directly in scope, but may inform ETS4
  readers through transferable methods, relevant datasets, or adjacent economic
  time-series applications.
- `borderline`: The fit is genuinely ambiguous. Use this when a reasonable
  editor could send it either to review or rejection.
- `not_relevant`: The paper is outside ETS4 scope for this issue.

Examples:

```json
"relevance_label": "directly_relevant"
```

```json
"relevance_label": "not_relevant"
```

### `expected_category`

Use the expected final category after triage. Valid values are currently:
`directly_relevant`, `paper_of_interest`, and `not_relevant`.

Rule of thumb: this usually mirrors `relevance_label`, except a
`borderline` relevance label should be resolved to the category the editor
expects ETS4 to use for scoring.

Examples:

```json
"relevance_label": "borderline",
"expected_category": "paper_of_interest"
```

```json
"relevance_label": "directly_relevant",
"expected_category": "directly_relevant"
```

### Practitioner/Applied Rubric Fields

These fields make the editorial product explicit.

`audience_fit`:

- `practitioner`: useful for forecasters, analysts, policymakers, risk managers,
  or other applied users.
- `applied_researcher`: useful for applied academic or institutional researchers.
- `academic_methods`: mainly methodological, with possible future transfer.
- `out_of_scope`: not useful for the ETS4 applied forecasting product.

`application_type`:

- `forecasting`
- `nowcasting`
- `scenario_analysis`
- `risk_monitoring`
- `forecast_evaluation`
- `method_only`
- `descriptive`
- `trading`
- `out_of_scope`

`economic_relevance`:

- `high`: directly macro, financial, policy, energy, business, or market relevant.
- `medium`: adjacent or transferable with clear adaptation.
- `low`: weakly connected or niche.
- `absent`: no meaningful economic forecasting relevance.

`forecasting_contribution`:

- `genuine_application`: real forecasting/nowcasting/risk/scenario task with
  usable evidence.
- `standard_application`: forecasting application exists, but contribution is
  routine or low-impact.
- `novel_method`: method is interesting, but applied value is not yet proven.
- `indirect`: useful context, dataset, scenario, or insight, but not a
  forecasting contribution.
- `absent`: no forecasting contribution.

`publication_track`:

- `deep_dive`: main applied forecasting recommendation.
- `applied_note`: short applied note; useful but not a main feature.
- `methods_watch`: academically interesting or potentially transferable, but
  not yet a practitioner recommendation.
- `reject`: out of scope, too weak, too routine, or not useful enough.

`social_hook_potential`:

- `high`
- `medium`
- `low`

This is dissemination metadata only. It should not override applied usefulness.

### `expected_triage_decision`

Allowed values:

- `assign_reviewers`: The paper should pass desk screening and enter full
  review consideration.
- `borderline`: The paper should be escalated rather than confidently accepted
  or rejected at triage.
- `reject`: The paper should not receive full review for this issue.

Examples:

```json
"expected_triage_decision": "assign_reviewers"
```

```json
"expected_triage_decision": "reject"
```

### `expected_editorial_decision`

Allowed values:

- `full_deep_dive`: Feature the paper with a substantive write-up.
- `short_mention`: Mention it briefly, but do not make it a main feature.
- `watchlist`: Track it for later, but do not publish it in the current issue.
- `needs_human_adjudication`: Do not let ETS4 make the final call automatically.
- `reject`: Do not include it.

Examples:

```json
"expected_editorial_decision": "full_deep_dive"
```

```json
"expected_editorial_decision": "needs_human_adjudication"
```

Use `needs_human_adjudication` when reviewer disagreement, evidence weakness,
ambiguous scope, or publication risk makes the automatic decision unsafe.

### `expected_deep_dive` and `expected_short_mention`

These booleans express expected publication selection, not relevance alone.

Rules of thumb:

- If `expected_editorial_decision` is `full_deep_dive`, set
  `expected_deep_dive` to `true` and `expected_short_mention` to `false`.
- If `expected_editorial_decision` is `short_mention`, set
  `expected_deep_dive` to `false` and `expected_short_mention` to `true`.
- For `watchlist`, `needs_human_adjudication`, or `reject`, usually set both to
  `false`.

Examples:

```json
"expected_editorial_decision": "full_deep_dive",
"expected_deep_dive": true,
"expected_short_mention": false
```

```json
"expected_editorial_decision": "watchlist",
"expected_deep_dive": false,
"expected_short_mention": false
```

### `required_evidence_kinds`

Use this list for the evidence kinds that ETS4 should have found for the paper
to support the expected review. Keep it empty for triage-only labels, rejected
papers, or papers with unavailable full text.

Common values:

- `method`
- `dataset`
- `metric`
- `baseline`
- `limitation`
- `code`

Examples:

```json
"required_evidence_kinds": ["method", "dataset", "metric", "baseline"]
```

```json
"required_evidence_kinds": []
```

### `hard_negative`

Set this to `true` when the paper is a plausible false positive that ETS4 should
learn to reject. Good hard negatives often contain time-series language,
macroeconomic terminology, causal inference, financial markets, or econometrics
without a forecasting contribution.

Examples:

```json
"relevance_label": "not_relevant",
"expected_triage_decision": "reject",
"hard_negative": true
```

```json
"hard_negative": false
```

### `high_value`

Set this to `true` when missing the paper would be a meaningful editorial
failure. Use it sparingly for papers that are central to ETS4's issue scope,
methodologically important, unusually useful to practitioners, or strong
candidate deep dives.

Examples:

```json
"relevance_label": "directly_relevant",
"expected_editorial_decision": "full_deep_dive",
"high_value": true
```

```json
"high_value": false
```

### Complete Examples

Full deep-dive candidate:

```json
{
  "label_status": "accepted",
  "human_notes": "Directly relevant inflation forecasting paper with usable evidence.",
  "relevance_label": "directly_relevant",
  "expected_category": "directly_relevant",
  "expected_triage_decision": "assign_reviewers",
  "expected_editorial_decision": "full_deep_dive",
  "expected_deep_dive": true,
  "expected_short_mention": false,
  "required_evidence_kinds": ["method", "dataset", "metric", "baseline"],
  "hard_negative": false,
  "high_value": true
}
```

Hard negative:

```json
{
  "label_status": "accepted",
  "human_notes": "Causal monetary policy paper without a forecasting task.",
  "relevance_label": "not_relevant",
  "expected_category": "not_relevant",
  "expected_triage_decision": "reject",
  "expected_editorial_decision": "reject",
  "expected_deep_dive": false,
  "expected_short_mention": false,
  "required_evidence_kinds": [],
  "hard_negative": true,
  "high_value": false
}
```

Ambiguous paper requiring human judgment:

```json
{
  "label_status": "accepted",
  "human_notes": "Potentially transferable method, but economic forecasting fit is unclear.",
  "relevance_label": "borderline",
  "expected_category": "paper_of_interest",
  "expected_triage_decision": "borderline",
  "expected_editorial_decision": "needs_human_adjudication",
  "expected_deep_dive": false,
  "expected_short_mention": false,
  "required_evidence_kinds": ["method", "limitation"],
  "hard_negative": false,
  "high_value": false
}
```

### Relevance Set

Labels:

- directly relevant
- paper of interest
- not relevant
- borderline

Include hard negatives:

- causal inference papers
- structural VAR papers without forecasting
- descriptive macro/finance papers
- theoretical econometrics without predictive application
- non-economic forecasting papers with transferable methods

### Evidence Set

For selected papers, label:

- key method claims
- datasets
- metrics
- baselines
- limitations
- whether the paper supports each claim

### Draft Quality Set

Human editor labels:

- keep as written
- minor edit
- major edit
- remove claim
- needs source check
- publication-ready

## Metrics

Selection:

- precision for selected papers
- recall for known relevant papers
- false-positive rate on hard negatives
- false-negative rate for high-value papers
- quality of top-k full-review selection
- quality of top-k deep-dive selection
- diversity across source, topic, method family, and target variable

Categorization:

- category accuracy
- borderline escalation rate
- confusion between direct relevance and paper of interest

Evidence:

- unsupported-claim rate
- citation coverage
- missing-limitation rate
- table/figure extraction coverage

Scoring:

- rank correlation with human labels
- calibration by score bucket
- inter-reviewer disagreement

Panel behavior:

- correct escalation of borderline papers
- preservation of minority reports
- rate of unresolved disagreements hidden from public drafts
- handling-editor decision accuracy

Draft usefulness:

- human edit distance
- number of unresolved editor questions
- accepted draft section rate
- time-to-publish proxy

## Evaluation Protocol

1. Freeze a benchmark dataset.
2. Run the current production review workflow.
3. Run the candidate workflow.
4. Compare structured outputs and draft quality.
5. Approve the candidate only if it improves target metrics without unacceptable regressions.

Prompt/model changes should be rejected if they:

- increase unsupported claims
- reduce precision on hard negatives
- degrade top-k selection quality under the same paper budget
- lower evidence coverage
- hide reviewer disagreement
- improve style while weakening factuality

## Gold Labels

Gold labels should be created by human review, not by another model. Models may
suggest labels, but the accepted benchmark should be manually inspected.

Each paper label can include `label_status`. If present, it must be `accepted`
before evaluation. This prevents draft template placeholders from being treated
as gold labels.

Benchmark labeling is a validation and regression-testing activity, not the
normal production scoring workflow. In production ETS4 should continue to use
agents or model providers to score, triage, review, and rank papers. The human
editor should not need to label every paper as benchmark data for every issue.

Human benchmark labels are still required when ETS4 needs an external quality
reference: during pilot validation, after prompt or provider changes, after
material source-mix changes, when quality appears to drift, or when comparing a
candidate workflow against the current baseline. Future automation may run the
collection, extraction, review, export, archive, and evaluation commands without
manual intervention, but it must not convert agent-generated judgments into
accepted gold labels.

Accepted labels may later support two distinct uses:

- **Evaluation holdout:** labels that agents must not see during a run, used to
  measure ETS4 quality.
- **Casebook examples:** labels that agents may retrieve as past editorial
  precedents when a new decision is uncertain.

Keep these pools separate. A casebook can help agents handle borderline
triage, `paper_of_interest` examples, hard negatives, and transferable-method
papers more consistently, but it should not contaminate holdout metrics. If
casebook retrieval is added, each run should record which labeled examples were
shown to the agent.

For the pilot, prefer a stable holdout benchmark so ETS4 changes can be compared
against a fixed reference. A rolling holdout, where old evaluated labels are
promoted into the casebook and new labels become the next private holdout, may
be useful later after multiple runs and broader source coverage.

## Regression Artifacts

Each evaluation run should store:

- code version
- prompt version
- model/provider/version
- source documents
- structured outputs
- metric summary
- qualitative error notes

## Minimum Standard Before SOTA Work

Before adding more advanced agentic behavior, ETS4 should have:

- at least 100 labeled triage examples
- at least 20 full-review examples
- hard-negative coverage
- benchmark command in CI or local test workflow
- documented acceptance thresholds for prompt/model changes
