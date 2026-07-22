# Testing

## Deterministic suite

Run:

```bash
python -m pytest
```

The suite uses temporary synthetic PDFs and mocked provider/network responses. It covers:

- local PDF and URL ingestion;
- narrow landing-page resolution and private-address rejection;
- unreadable and image-only failures;
- prompt-injection data separation;
- panel count and coverage validation;
- harmonized answer and recommendation enums;
- typed dynamic prompt rendering;
- OpenAI Responses/native-PDF payload construction;
- strict Structured Outputs compatibility and non-retryable sanitized `BadRequestError` diagnostics;
- configurable concurrent isolated referees;
- partial-referee failure and final-editor blocking;
- resume without repeated successful calls;
- planned-versus-realized coverage integrity;
- raw-retention switches, secret redaction, artifacts, and CLI behavior;
- complete mock-provider end-to-end execution at default and non-default counts.

## Static validation

```bash
python -m ruff check src tests evals
python -m mypy src/ets4 evals/build_case_pdf.py
python -m py_compile $(find src/ets4 evals -name '*.py' -type f | sort)
git diff --check
```

Use Python 3.12 for release validation. Compatibility with older local interpreters is not a supported package guarantee.

## Behavioral evaluations

Schema tests cannot prove intellectual quality. `evals/criteria-v1.json` defines versioned human-review criteria for panel fit/differentiation, Stage 1 non-anchoring, referee independence and remit behavior, final synthesis categories, and realized coverage. `evals/cases/synthetic_forecast_combination_v1.md` and its metadata provide a fixed behavioral case; `evals/build_case_pdf.py` creates its complete PDF input.

Behavioral evaluations use public or synthetic manuscripts and stored artifacts. They are not default unit tests and should never require a live provider in CI. Record provider/model, prompt versions, reasoning/output settings, manuscript hash, evaluator, rubric version, and results.

## Live providers

Live tests must:

- use an explicit `live` marker;
- be disabled by default;
- require environment credentials;
- show expected maximum calls/cost before execution;
- use authorized public or synthetic manuscripts;
- write only ignored run artifacts.

No deterministic test may depend on a live API response.

The Stage 1 transport smoke test makes exactly one paid initial-editor request, uses `gpt-5.6`, a small synthetic PDF, two requested profiles, and the production `EditorPanelDesign` schema. It cannot create referee jobs:

```bash
export OPENAI_API_KEY=...
ETS4_RUN_LIVE_OPENAI=1 python -m pytest \
  tests/test_live_openai_stage1.py -v
```
