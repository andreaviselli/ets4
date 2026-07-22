# Review protocol

## Aim

ETS4 produces specialized AI referee reports for economic time-series forecasting papers. It supports human review; it does not replace it.

The process has one initial editor, a fixed panel of separate referees, and one final editor. The initial and final editor are the same logical role, linked by saved data rather than a hidden model session.

Every editor and referee is asked to write in plain English, avoid needless jargon, and use an informal but objective tone.

## Stage 1: initial editor

Input: only the complete manuscript.

Output: an `EditorPanelDesign` with:

- five to eight main components or claims that need review;
- the requested number of distinct, realistic referee profiles;
- a planned coverage table using P, S, and Blank;
- remaining gaps and unavoidable overlap.

The panel should fit the paper, cover its main claims, include deep expertise, and avoid duplicate roles. Background differences matter only when they improve coverage.

Each profile has a stable ID, a role, a research viewpoint, main expertise, three to five specialist topics, a broad task for this paper, a unique contribution, and areas where the referee is not the main authority.

Every review need has at least one P. More than two P assignments are allowed only for a need marked as part of the central claim.

The initial editor must not identify suspected errors, write review comments, prescribe checks, name real researchers, steer a referee toward a conclusion, or predict the final decision.

## Stage 2: independent referees

Each referee gets a new provider call containing:

- the complete PDF;
- the shared referee instructions;
- only that referee's profile;
- the `RefereeReport` output format.

A referee gets no other profile, report, editor summary, shared conversation, or tool. Separate calls keep contexts apart, but outputs from the same model family may still have similar biases.

Each report includes one of Accept, Minor revision, Major revision, or Reject; answers to seven shared questions; a neutral summary; an overall view; ordered major comments; a short list of minor comments; private comments for the editor; confidence; and any ethics or integrity concern.

The seven questions cover the forecasting contribution, literature position, scientific soundness, forecast evaluation, conclusions, limitations, and presentation or replication. Answers are limited to Yes, Mostly, Partly, No, and Not applicable.

Referees must not assume the paper is flawed, force their preferred method, request unrelated work, invent references, or ask for a robustness check without explaining the alternative cause it tests. Reports should stay near two pages.

## Stage 3: final editor

Input:

- the complete manuscript;
- the checked Stage 1 design and original coverage table;
- exactly all configured referee reports.

Stage 1 explains why the panel was built. It is not another report or vote.

The final editor starts with a neutral summary and checks whether the claims, evidence, and conclusions line up. The report is organized by issue, not by referee. Similar comments are merged without losing important differences in reasoning.

Each main issue says where it applies, what is missing, why it matters, what should change, and what the editor concludes. A short line records panel status, validity, importance, severity, and whether the issue can be fixed. Referee-specific reasoning stays in JSON for audit.

Panel status is kept separate:

- consensus: several reports reach the same point through their own reasoning;
- specialist contribution: a well-supported point from relevant expertise;
- disagreement: reports differ in a meaningful way, resolved only when the manuscript supports a resolution.

The editor does not vote, average scores, count recommendations, add a new open-ended review, or invent unrelated criticism.

The final recommendation is exactly one of Accept, Minor revision, Major revision, Reject and resubmit, or Reject. It follows from the contribution, the validity and importance of the issues, and whether they can be fixed.

## Coverage appendix

For every original table cell, actual reasoning is coded as P, S, or Blank and shown beside the plan. A matching keyword does not count as real coverage.

The appendix notes what was covered, what was missed, useful unplanned work, too much overlap, and whether the referee roles stayed distinct. It assesses the panel only. It cannot add referees, invent criticism, or change the recommendation merely because coverage was weak.

## Failures

- Inaccessible or incomplete manuscript: stop before model review.
- Invalid Stage 1 output: make only the allowed repair and retry attempts, then wait for resume.
- One failed referee: keep successful reports, block Stage 3, and resume only missing or failed work.
- Invalid final coverage table: reject the final output and require a retry.
- User cancellation: save `cancelled` and do not resume automatically.
