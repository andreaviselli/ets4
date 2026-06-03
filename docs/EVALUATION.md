# Evaluation

ETS4 should treat evaluation as a production requirement. A review system that
cannot be measured will drift toward polished but unreliable prose.

## Evaluation Goals

The system should be evaluated for:

- relevance selection quality
- category accuracy
- evidence support
- scoring calibration
- reviewer disagreement handling
- draft usefulness for human editing
- regression stability across prompt/model changes

## Benchmark Sets

Create small, high-quality labeled sets before scaling.

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
- lower evidence coverage
- hide reviewer disagreement
- improve style while weakening factuality

## Gold Labels

Gold labels should be created by human review, not by another model. Models may
suggest labels, but the accepted benchmark should be manually inspected.

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
