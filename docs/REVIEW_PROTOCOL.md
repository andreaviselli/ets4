# Review protocol

## Aim

ETS4 produces specialized AI referee reports for economic time-series forecasting papers. It supports human review; it does not replace it.

The process has one initial editor, a fixed panel of separate referees, and one final editor. The initial and final editor are the same logical role, linked by saved data rather than a hidden model session.

Every editor and referee is asked to write in plain English, avoid needless jargon, and use an informal but objective tone.

## Stage 1: initial editor

Stage 1 has two separate, application-controlled calls.

The requirement-discovery call receives only the complete manuscript. The user chooses either an exact number from one through ten or auto mode. Exact mode asks for that number. Auto mode gives the editor no number, range, or application cap. The editor orders the requirements from most to least important.

In auto mode, ETS4 retains the first ten requirements. If more were returned, it records a warning and excludes the later requirements from panel design and all later stages. The cap is not present in the discovery prompt or structured-output schema. Discarded text exists only in the optional raw provider response.

The panel-design call receives the complete manuscript and only the retained requirements. It returns an `EditorPanelDesign` with:

- the retained main components or claims, unchanged and in order;
- the requested number of distinct, realistic referee profiles;
- a planned coverage table using P, S, and Blank;
- remaining gaps and unavoidable overlap.

The panel should fit the paper, cover its main claims, include deep expertise, and avoid duplicate roles. Background differences matter only when they improve coverage.

Each profile has a stable ID, a role, a research viewpoint, main expertise, three to five specialist topics, a broad task for this paper, a unique contribution, and areas where the referee is not the main authority.

Every retained review need has at least one P. More than two P assignments are allowed only for a need marked as part of the central claim.

The initial editor must not identify suspected errors, write review comments, prescribe checks, name real researchers, steer a referee toward a conclusion, or predict the final decision.

## Stage 2: independent referees

Each referee gets a new provider call containing:

- the complete PDF;
- the shared referee instructions;
- only that referee's profile;
- the `RefereeReport` output format.

A referee gets no other profile, report, editor summary, shared conversation, or tool. Separate calls keep contexts apart, but outputs from the same model family may still have similar biases.

Each report includes one of Accept, Minor revision, Major revision, or Reject; answers to seven shared questions; a neutral summary; an overall view; ordered major comments; a short list of minor comments; private comments for the editor; confidence; and any ethics or integrity concern. Confidence remains in JSON for audit but is not printed in the readable report.

The seven questions cover the forecasting contribution, literature position, scientific soundness, forecast evaluation, conclusions, limitations, and presentation or replication. Answers are limited to Yes, Mostly, Partly, No, and Not applicable.

Each major comment is one natural prose passage without a stylized title or labelled Concern and Affected claim lines. It follows the manuscript's language and notation and supports the criticism with a concrete verbal or mathematical example. Manuscript locations remain in JSON for audit rather than appearing as a separate reader-facing label.

Before finalizing, the referee reviews every criticism a second time against the complete manuscript, its supporting example, and its logic. The referee corrects overstatement and errors, but does not drop a criticism merely because uncertainty remains; any remaining uncertainty is stated plainly.

Referees must not assume the paper is flawed, force their preferred method, request unrelated work, invent references, search for external references, or ask for a robustness check without explaining the alternative cause it tests. Reports should stay near two pages.

## Stage 3: final editor

Input:

- the complete manuscript;
- the checked Stage 1 design and original coverage table;
- exactly all configured referee reports.

Stage 1 explains why the panel was built. It is not another report or vote.

The final editor starts with a Summary and checks whether the claims, evidence, and conclusions line up. The report is organized by issue under Referee comments, not by referee. Similar comments are merged without losing important differences in reasoning.

Each main issue is one natural prose passage of at most 2,000 characters. It explains where the issue applies, what is missing, why it matters, what should change, and what the editor concludes without rigid labels, titles, or tags. The editor follows the manuscript's language and notation and gently translates needlessly formal referee wording. Panel status, validity, importance, severity, correctability, and referee-specific reasoning stay in JSON for audit.

Panel status is kept separate:

- consensus: several reports reach the same point through their own reasoning;
- specialist contribution: a well-supported point from relevant expertise;
- disagreement: reports differ in a meaningful way, resolved only when the manuscript supports a resolution.

The editor does not vote, average scores, count recommendations, add a new open-ended review, or invent unrelated criticism.

The final report does not contain separate sections for principal strengths, decision-determining issues, essential revisions, or desirable but non-essential improvements. The Recommendation section contains exactly one of Accept, Minor revision, Major revision, Reject and resubmit, or Reject and explains how it follows from the contribution, the validity and importance of the issues, and whether they can be fixed.

## Coverage appendix

For every original table cell, actual reasoning is coded as P, S, or Blank and shown beside the plan. A matching keyword does not count as real coverage.

The appendix notes what was covered, what was missed, useful unplanned work, too much overlap, and whether the referee roles stayed distinct. It assesses the panel only. It cannot add referees, invent criticism, or change the recommendation merely because coverage was weak.

## Failures

- Inaccessible or incomplete manuscript: stop before model review.
- Invalid requirement discovery or panel design: make only the allowed repair and retry attempts, then wait for resume.
- One failed referee: keep successful reports, block Stage 3, and resume only missing or failed work.
- Invalid final coverage table: reject the final output and require a retry.
- User cancellation: save `cancelled` and do not resume automatically.
