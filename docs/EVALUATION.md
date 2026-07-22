# Behavioral evaluation

## Purpose

ETS4 evaluation separates structural correctness from editorial behavior. Pydantic and workflow tests establish count, enum, isolation, completeness, and persistence invariants. Human review is required for whether the panel and reports are actually good.

## Versioned criteria

The first rubric is `evals/criteria-v1.json` and includes:

- manuscript fit and panel differentiation;
- full requirement coverage without implausible omniscience;
- absence of suspected-error anchoring in Stage 1;
- referee independence and no cross-report leakage;
- specialist remit compliance without mechanical restriction;
- consequential, manuscript-grounded comments rather than forced criticism;
- separation of consensus, specialist contributions, and disagreements;
- issue-based final synthesis rather than voting;
- substantive planned-versus-realized coverage coding;
- recommendation justification based on contribution, severity, centrality, and correctability.

## Evaluation record

For each case, record:

- rubric version;
- manuscript SHA-256 and public/synthetic provenance;
- run ID and input fingerprint;
- provider, models, prompt versions, reasoning, and output settings;
- human evaluator and date;
- criterion score, evidence, and critical-failure status;
- overall accept/revise/reject decision for the provider configuration.

## Acceptance policy

Any critical failure in confidentiality, context isolation, complete-manuscript access, Stage 1 anchoring, missing-report fan-in, or invented final-editor criticism rejects the candidate configuration.

Non-critical failures should be corrected conceptually and tested on a held-out manuscript. Do not tune to one paper or accept prose fluency as review quality.
