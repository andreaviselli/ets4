# Testing

## Normal test suite

Run:

```bash
python -m pytest
```

The suite uses temporary synthetic PDFs and mocked network or provider responses. It covers:

- local and URL PDF input;
- safe landing-page links and rejection of private addresses;
- broken and image-only files;
- separation of manuscript data from prompts;
- panel counts and coverage rules;
- allowed answers and recommendations;
- prompt variables and packaged prompt versions;
- OpenAI PDF requests and structured output;
- safe handling of OpenAI schema and API errors;
- separate parallel referee calls;
- partial failure, blocked final editing, and resume;
- planned versus actual coverage;
- raw-response settings, secret hiding, run files, and CLI commands;
- full mock reviews at default and non-default panel sizes;
- both `ets4` and `python -m ets4` entry points.

## Static checks

```bash
python -m ruff check src tests evals
python -m mypy src/ets4 evals/build_case_pdf.py
python -m py_compile $(find src/ets4 evals -name '*.py' -type f | sort)
git diff --check
```

Use Python 3.12 for release checks. Older Python versions are not supported.

## Human evaluation

Schema tests cannot judge intellectual quality. `evals/criteria-v1.json` scores panel fit, referee separation and role use, Stage 1 neutrality, final issue handling, and actual coverage. The fixed synthetic case lives in `evals/cases/`, and `evals/build_case_pdf.py` turns it into a PDF.

Human checks use public or synthetic manuscripts and saved run files. They are not normal unit tests and must not require a live provider in CI. Record all settings, prompt versions, manuscript hash, evaluator, scoring-guide version, evidence, and result.

## Live provider test

A live test must be marked `live`, stay off by default, require an environment key, state its maximum calls or cost, use an approved public or synthetic paper, and write only ignored run output.

The current OpenAI smoke test makes one paid initial-editor call with a small synthetic PDF and cannot start referees:

```bash
export OPENAI_API_KEY=...
ETS4_RUN_LIVE_OPENAI=1 python -m pytest \
  tests/test_live_openai_stage1.py -v
```

## Built-package test

Before release, build the wheel and source archive, inspect their file lists, install the wheel in a clean Python 3.12 environment, and run both CLI entry points plus a mock review from outside the checkout. The full checklist is in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).
