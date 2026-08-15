# Human evaluation

## Why it exists

Normal tests can prove that ETS4 uses the right counts, values, stage order, separation, and saved files. They cannot prove that a referee panel or report is intellectually good. That needs human judgment.

## Scoring guide

`evals/criteria-v3.json` checks:

- whether the panel fits the paper and gives referees distinct roles;
- whether important claims are covered without impossible all-purpose experts;
- whether Stage 1 avoids planting suspected errors;
- whether auto discovery avoids obvious count anchoring and ranks the most important requirements first;
- whether separating discovery from panel design improves coverage enough to justify its added call;
- whether referees stay separate and do not leak other reports;
- whether each referee uses their expertise without following the profile mechanically;
- whether comments are important and grounded in the paper rather than forced;
- whether major criticisms use the manuscript's language and notation, include useful examples, and avoid errors or overstatement after the required second check;
- whether referee and final-editor comments read as natural prose without rigid titles, labels, or tags;
- whether the final editor separates agreement, specialist points, and disagreement;
- whether the final report is organized by issue instead of votes;
- whether planned and actual coverage are compared from real reasoning;
- whether the recommendation follows from valid, important, and fixable issues.

Version 3 covers the referee and final-editor `1.2.0` prompts. Version 2 remains the guide for two-step Stage 1 runs that use the earlier report format.

## Evaluation record

For each case, record the scoring-guide version, manuscript hash and source, run ID and fingerprint, provider and models, prompt versions, model settings, evaluator and date, score evidence, critical failures, and the overall decision on that configuration.

## Acceptance rule

Reject a configuration if it exposes confidential context, mixes referee contexts, omits part of the manuscript, lets Stage 1 plant a criticism, runs the final editor with missing reports, or lets the final editor invent criticism.

For other failures, fix the underlying idea and test it on a different paper. Fluent prose alone is not evidence of a good review.
