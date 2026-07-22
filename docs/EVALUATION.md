# Human evaluation

## Why it exists

Normal tests can prove that ETS4 uses the right counts, values, stage order, separation, and saved files. They cannot prove that a referee panel or report is intellectually good. That needs human judgment.

## Scoring guide

`evals/criteria-v1.json` checks:

- whether the panel fits the paper and gives referees distinct roles;
- whether important claims are covered without impossible all-purpose experts;
- whether Stage 1 avoids planting suspected errors;
- whether referees stay separate and do not leak other reports;
- whether each referee uses their expertise without following the profile mechanically;
- whether comments are important and grounded in the paper rather than forced;
- whether the final editor separates agreement, specialist points, and disagreement;
- whether the final report is organized by issue instead of votes;
- whether planned and actual coverage are compared from real reasoning;
- whether the recommendation follows from valid, important, and fixable issues.

## Evaluation record

For each case, record the scoring-guide version, manuscript hash and source, run ID and fingerprint, provider and models, prompt versions, model settings, evaluator and date, score evidence, critical failures, and the overall decision on that configuration.

## Acceptance rule

Reject a configuration if it exposes confidential context, mixes referee contexts, omits part of the manuscript, lets Stage 1 plant a criticism, runs the final editor with missing reports, or lets the final editor invent criticism.

For other failures, fix the underlying idea and test it on a different paper. Fluent prose alone is not evidence of a good review.
