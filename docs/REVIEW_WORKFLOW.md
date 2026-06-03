# Review Workflow

The review workflow exists to make editorial judgment explicit. ETS4 should not
select papers because a single model produced a high score. A paper should be
selected because it passes a sequence of evidence-backed gates.

## Review Objects

Each review run should produce structured records:

- paper identity and source metadata
- extracted evidence items
- reviewer outputs
- disagreement notes
- final editorial decision
- public draft text
- internal human-review notes

## Gates

### Gate 1: Scope Triage

Question: is this plausibly relevant to economic time-series forecasting?

Inputs:

- title
- abstract
- source
- authors
- metadata

Required output:

- `in_scope`: boolean
- `scope_reason`
- `forecasting_signal`: explicit, implied, absent
- `economic_signal`: explicit, implied, absent
- `triage_confidence`

Gate rule:

- Reject if forecasting signal is absent.
- Reject if relevance is only causal, descriptive, or purely theoretical.
- Send borderline cases to full review rather than forcing a confident label.

### Gate 2: Evidence Extraction

Question: what source-backed claims can be reviewed?

Inputs:

- full text when available
- abstract when full text is unavailable
- extracted tables, figures, metrics, datasets, and baselines

Required output:

- evidence items with source locators
- missing-evidence flags
- extraction failures

Gate rule:

- A full deep dive requires full-text evidence.
- Abstract-only review must be labeled as limited.

### Gate 3: Specialist Reviews

Run independent reviewers with narrow mandates.

Relevance reviewer:

- forecasting objective
- economic time-series relevance
- target variables and decision context

Methods reviewer:

- methodological novelty
- model class
- assumptions
- transferability
- likely failure modes

Evidence reviewer:

- datasets
- train/test design
- baselines
- evaluation metrics
- robustness checks
- unsupported claims

Practitioner reviewer:

- decision value
- implementation burden
- interpretability
- uncertainty usefulness
- audience fit

Each reviewer must return structured JSON and cite evidence item ids.

### Gate 4: Reconciliation

Question: do the reviewers agree enough to make an editorial decision?

The reconciler should identify:

- major disagreements
- missing evidence
- overclaiming risk
- score/category conflicts
- questions for the human editor

Gate rule:

- High novelty plus weak evidence should not become a high-confidence recommendation.
- Direct relevance and paper-of-interest labels should be justified separately from score.

### Gate 5: Editor Pass

Question: what should be published, and with what caveats?

Outputs:

- final decision: reject, watchlist, short mention, full deep dive
- publication category
- public summary
- critical caveats
- human-review checklist
- confidence rating

The editor pass writes for the target audience but must not add claims absent
from the review record.

## Scoring

Use separate dimensions instead of a single opaque score:

- forecasting relevance
- economic relevance
- methodological novelty
- empirical credibility
- practical value
- evidence quality
- transferability

The final recommendation can derive from these dimensions, but the dimensions
must remain visible in internal notes.

## Human Review Output

Every draft should include a companion internal file with:

- accepted claims and source evidence
- unsupported or weak claims removed from public prose
- questions for the editor
- assumptions and confidence flags
- rejected-but-interesting papers
- model/version metadata

## Failure Modes To Guard Against

- treating causal inference as forecasting
- summarizing from the abstract as if full evidence was read
- praising novelty without baseline comparison
- ignoring negative or mixed empirical results
- confusing methodological sophistication with practical usefulness
- overfitting the newsletter to what one model finds exciting
