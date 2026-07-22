# Implementation plan

Last updated: 2026-07-14

## Milestones

| Milestone | Status | Evidence |
| --- | --- | --- |
| Read repository handoff and all supplied sources | Complete | Four PDFs text-extracted and visually reviewed; hashes recorded |
| Preserve prior repository state and branch | Complete | Archival tag plus `codex/targeted-review-engine` |
| Replace obsolete product architecture | Complete | New ingestion, prompts, schemas, providers, workflow, storage, rendering, CLI |
| Add deterministic and behavioral evaluation foundations | Complete | Mock E2E tests, fixed synthetic case, PDF builder, and `evals/criteria-v1.json` |
| Synchronize documentation and ADRs | Complete | Required docs and provider/security/privacy records added |
| Full verification and final diff review | Complete | Python 3.12 test, lint, type, compile, diff, and path/secret checks pass |

## Key decisions

- Fixed application-controlled workflow rather than model-directed handoffs.
- Complete canonical PDF for every agent; page text is validation/fallback support.
- Inline OpenAI Responses file input and Pydantic Structured Outputs.
- Local atomic file persistence with explicit raw-response retention.
- Local CLI first; hosted API is a contract skeleton only.

## Required final verification

```bash
python -m pytest
python -m ruff check src tests evals
python -m mypy src/ets4 evals/build_case_pdf.py
python -m py_compile $(find src/ets4 evals -name '*.py' -type f | sort)
git diff --check
```
