# Review Workflow

The review workflow exists to make editorial judgment explicit. ETS4 should not
select papers because a single model produced a high score. A paper should be
selected because it passes a sequence of evidence-backed gates.

## Editorial Roles

ETS4 should model a small editorial panel, not a single monolithic reviewer.
Each role has a limited mandate and should write a separate structured report.

Managing editor:

- defines the issue scope
- sets source coverage and cost limits
- performs desk screening
- assigns reviewers
- makes the final publication decision

Handling editor:

- coordinates one paper or cluster of papers
- checks whether reviewer reports answer the right questions
- asks for additional review when evidence is weak or disagreement is material
- prepares the final editorial recommendation

Specialist reviewers:

- review independently
- cite evidence item ids
- expose uncertainty instead of smoothing it away
- do not see each other's reports until after independent review is complete

Copy editor:

- turns approved review records into readable public prose
- preserves caveats, uncertainty, and evidence boundaries
- does not introduce new technical claims

Human editor:

- reviews the draft, internal notes, and unresolved questions
- accepts, edits, rejects, or defers publication

## Review Objects

Each review run should produce structured records:

- paper identity and source metadata
- extracted evidence items
- assigned editorial roles
- reviewer outputs
- reviewer independence metadata
- disagreement notes
- final editorial decision
- public draft text
- internal human-review notes

## Gates

### Gate 0: Issue Setup

Question: what is this run allowed to do?

Inputs:

- issue date
- source registry version
- model/provider configuration
- cost budget
- source lookback window
- publication target
- automation mode: manual, scheduled-draft, or evaluation

Required output:

- `run_id`
- `issue_id`
- `source_snapshot_id`
- `prompt_version`
- `model_policy`
- `cost_budget`
- `allowed_actions`

Gate rule:

- Scheduled automation may collect, review, export drafts, and optionally open a
  pull request. It must not publish.
- A run without a manifest cannot produce publication artifacts.

### Gate 1: Desk Screening

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
- `desk_decision`: reject, borderline, assign_reviewers
- `triage_confidence`

Gate rule:

- Reject if forecasting signal is absent.
- Reject if relevance is only causal, descriptive, or purely theoretical.
- Send borderline cases to full review rather than forcing a confident label.

### Gate 2: Reviewer Assignment

Question: what expertise is needed to review this paper fairly?

Required output:

- assigned reviewer roles
- rationale for each assignment
- required evidence types
- known conflicts or limitations

Gate rule:

- A paper selected for full review should receive at least two independent
  specialist reviews.
- A methods-heavy paper needs a methods reviewer and an evidence reviewer.
- A non-economic paper labeled as transferable needs an explicit transferability
  reviewer.

### Gate 3: Evidence Dossier

Question: what source-backed claims can be reviewed?

Inputs:

- full text when available
- abstract when full text is unavailable
- extracted tables, figures, metrics, datasets, and baselines

Required output:

- evidence items with source locators
- claim candidates
- missing-evidence flags
- extraction failures

Gate rule:

- A full deep dive requires full-text evidence.
- Abstract-only review must be labeled as limited.
- Every public technical claim must later map to at least one evidence item or be
  marked as editorial interpretation.

### Gate 4: Independent Specialist Reviews

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

Transferability reviewer:

- whether a non-economic method could plausibly transfer to economic time series
- required adaptation
- assumptions that may fail in economic data
- expected value relative to existing economic forecasting methods

Each reviewer must return structured JSON and cite evidence item ids. Reviewer
reports should be generated independently before any synthesis step. The system
should preserve minority reports rather than averaging them away.

### Gate 5: Panel Reconciliation

Question: do the reviewers agree enough to make an editorial decision?

The reconciler should identify:

- major disagreements
- missing evidence
- overclaiming risk
- score/category conflicts
- questions for the human editor
- majority and minority views
- decision-critical uncertainty

Gate rule:

- High novelty plus weak evidence should not become a high-confidence recommendation.
- Direct relevance and paper-of-interest labels should be justified separately from score.
- If reviewers disagree on scope, evidence quality, or practical value, the paper
  should be marked `needs_editor` unless the handling editor resolves the issue
  with explicit reasoning.

### Gate 6: Handling Editor Decision

Question: what should be published, and with what caveats?

Outputs:

- final decision: reject, watchlist, short mention, full deep dive, needs human adjudication
- publication category
- decision memo
- critical caveats
- human-review checklist
- evidence confidence
- novelty confidence
- relevance confidence
- editorial confidence

The handling editor must decide whether reviewer disagreement is acceptable,
whether caveats are strong enough, and whether the paper deserves scarce editorial
space in the issue.

### Gate 7: Draft QA

Question: is the generated draft faithful to the review record?

Required output:

- claim ledger mapping public claims to evidence ids
- unsupported claims removed or flagged
- caveats preserved
- draft status: blocked, needs human edits, ready for human review

Gate rule:

- No paragraph containing a technical claim should enter the public draft without
  a claim-ledger entry.
- The draft must not hide major reviewer disagreement.
- `draft: true` is mandatory for exported pages.

The copy editor writes for the target audience but must not add claims absent
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

Scores should not be averaged mechanically. A severe weakness in evidence quality
or scope relevance can veto publication even if novelty is high.

## Human Review Output

Every draft should include a companion internal file with:

- accepted claims and source evidence
- unsupported or weak claims removed from public prose
- questions for the editor
- assumptions and confidence flags
- rejected-but-interesting papers
- model/version metadata
- panel disagreement summary
- claim ledger
- final human decision field

## Failure Modes To Guard Against

- treating causal inference as forecasting
- summarizing from the abstract as if full evidence was read
- praising novelty without baseline comparison
- ignoring negative or mixed empirical results
- confusing methodological sophistication with practical usefulness
- overfitting the newsletter to what one model finds exciting
- collapsing genuine reviewer disagreement into a smooth consensus
- allowing good prose to mask weak evidence
- letting scheduled automation publish without human approval
