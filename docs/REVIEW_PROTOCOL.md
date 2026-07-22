# Review protocol

## Objective

ETS4 produces automatic, specialized, targeted artificial referee reports for economic time-series forecasting manuscripts. It is an experiment intended to complement human review, not replace it.

The protocol has one initial editor, a configured panel of operationally isolated referees, and one final editor synthesis. The initial and final editor calls represent the same logical editorial role through explicit artifact handoff; they do not share hidden session state.

Every editor and referee writes in plain English, avoids convoluted or unnecessarily technical language, and uses an informal style and tone while remaining objective.

## Stage 1: initial editor

Input: the complete canonical manuscript only.

Output: `EditorPanelDesign` containing:

- five to eight principal components or claims;
- the configured number of realistic, distinct profiles;
- a planned coverage matrix using P, S, and Blank;
- panel gaps and unavoidable overlap.

Panel objectives are manuscript fit, coverage, vertical expertise, marginal contribution, limited redundancy, and realism. Diversity of background is used only when it improves coverage or reduces redundancy.

Every profile contains a stable identifier, functional slot, research orientation, primary expertise, three to five specialist topics, broad audit mandate, unique panel contribution, and non-authority areas.

Every requirement has at least one P. More than two P assignments are allowed only for a requirement explicitly marked as concerning validity of the central claim.

Stage 1 must not identify suspected errors, write review comments, prescribe checks or extensions, name real researchers, tell referees what conclusion to reach, or anticipate the final decision.

## Stage 2: independent referees

Every profile creates one stateless provider call with:

- the complete PDF;
- common referee instructions;
- only that profile and its neutral remit;
- the `RefereeReport` schema.

It receives no other profile, report, editor synthesis, shared mutable context, or tool. Operational independence does not claim statistical independence between outputs from the same model family.

Each report contains one of Accept, Minor revision, Major revision, or Reject; all seven harmonized answers; a neutral summary; overall assessment; prioritized major comments; limited minor comments; confidential editor comments; confidence; and ethical/integrity status.

The seven questions concern forecasting contribution, literature position, scientific soundness, forecasting evaluation, conclusions, limitations, and presentation/replication. Answers are limited to Yes, Mostly, Partly, No, and Not applicable.

Referees must not assume defect, force a preferred method, request unrelated extensions, invent references, or propose robustness exercises without naming the alternative explanation addressed. Reports should remain approximately two pages.

## Stage 3: final editor

Input:

- the complete manuscript;
- validated Stage 1 design and original matrix;
- exactly all configured validated reports.

Stage 1 explains intended coverage but is not another report or corroborating vote.

The final editor begins with a neutral summary and assesses contribution and claim/evidence/conclusion alignment. Synthesis is organized by issue, not referee. Equivalent comments are merged without erasing materially different reasoning.

Each principal issue records a short title, where it applies, what is missing, why it matters, what needs to change, the editor's adjudicated view, supporting referee reasoning, validity, centrality, severity, and correctability. The Markdown report presents the six reader-facing sections followed by one compact assessment line; referee-specific reasoning remains in structured JSON for audit. Panel status is explicitly separated into:

- consensus: convergent, separately articulated reasoning;
- specialist contribution: supported reasoning from pertinent expertise;
- disagreement: materially different assessments, resolved only when manuscript evidence permits.

The editor does not vote, average, count recommendations, add an open-ended review, or introduce unrelated criticism.

Final recommendation is exactly one of Accept, Minor revision, Major revision, Reject and resubmit, or Reject. It follows from contribution validity, issue severity and centrality, and feasibility of correction.

## Coverage appendix

For every original matrix cell, actual reasoning is classified as P, S, or Blank and rendered as planned-to-actual notation. Keyword occurrence is not substantive coverage.

The appendix records covered dimensions, under-coverage, unplanned contributions, excessive overlap, and functional differentiation. It diagnoses panel design only. It does not add reviewers, invent criticism, or change the recommendation merely because coverage was weak.

## Failure behavior

- Inaccessible or incomplete manuscript: stop before model review.
- Invalid Stage 1 output: bounded repair/retry, then `awaiting_retry`.
- One failed referee: persist successful reports, block Stage 3, and resume only missing/failed work.
- Invalid final coverage mapping: reject final output and require retry.
- Explicit cancellation: persist `cancelled`; do not resume automatically.
