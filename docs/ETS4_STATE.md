# ETS4 state

Last updated: 2026-07-22

## Current milestone

ETS4 is now the targeted manuscript-review tool described in the July 2026 brief and four source PDFs. The old forecasting digest is preserved at tag `archive/pre-targeted-review-2026-07-14` (commit `8d3be59`). Work remains on branch `codex/targeted-review-engine`.

The local workflow is working. Two OpenAI reviews of real papers completed the initial editor, four separate referees, final editor, and report rendering. The user found both results useful. This is practical evidence, not a guarantee that every PDF or model judgment will succeed.

## What works

- Local and supported-URL PDF input with hashing, every-page text extraction, file and page limits, narrow landing-page rules, redirect checks, and private-address blocking.
- One manuscript package containing the unchanged PDF, metadata, and page text.
- Versioned prompts for the initial editor, referees, and final editor. Version `1.1.0` asks for plain, informal, objective writing.
- Checked Pydantic models for panel design, referee reports, final issues, and planned-versus-actual coverage.
- A Python-controlled workflow with separate referee calls, limited parallel work, bounded retries, saved progress, cancellation, and resume without repeating completed paid calls.
- A free repeatable mock provider and an OpenAI Responses API provider with inline PDF input, strict structured output, no tools, set timeouts, stage-specific models, `store=false` by default, and safe errors.
- CLI commands for `review`, `resume`, `status`, `cancel`, `validate-config`, and `providers`.
- JSON and Markdown reports, usage data, event logs, and optional raw responses.
- Normal tests plus a fixed synthetic paper and human scoring guide under `evals/`.

## Package and documentation update

- The README covers direct GitHub installation, Jupyter `%pip`, local checkout installation, and first-run Python examples for both mock and OpenAI reviews. Editable installs are clearly marked for development.
- Both `ets4` and `python -m ets4` run the CLI.
- Package metadata now lists the console environment, Python 3.12, typing support, repository links, and keywords. The wheel contains `py.typed` and every prompt version.
- `docs/README.md` now gives the documentation a clear entry point.
- The README, `AGENTS.md`, and all active docs were rewritten in plainer English while keeping the review, security, and privacy rules.
- Old empty `data/` and `exports/` placeholders and the one-off `docs/QUICK_PROMPT.txt` were removed. Ignored local databases, exports, manuscripts, and run directories were not deleted.
- `docs/IMPLEMENTATION_PLAN.md` now covers the remaining package-release work. A licence choice and clean release process are still required before public publication.

## Current checks

Checks ran on Python 3.12.13:

- `python -m pytest`: 47 passed and one opt-in live test skipped; only five third-party PyMuPDF warnings;
- Ruff: passed;
- mypy: passed;
- Python compile check: passed;
- `git diff --check`: passed;
- all local Markdown links: passed;
- wheel build and file inspection: passed, including `py.typed` and all `1.0.0` and `1.1.0` prompt files;
- the installed wheel ran both CLI entry points and completed a three-referee mock review from outside the repository.

The synthetic PDF kept its expected SHA-256: `0fa4de1833db57fd71071163b6a9430e978a1147a45b941f1888d35b8e9d41e1`.

## Live OpenAI schema incident

An early run, `run-746d588dcd6d`, failed before Stage 1 because OpenAI rejected a coverage dictionary in the strict JSON schema. ETS4 replaced that dictionary with typed coverage cells and now checks output shapes before making a paid call.

That old run cannot resume because it predates the stored schema hashes and SDK version. It made no referee calls. Later runs used the corrected format and completed. Errors keep only safe fields and never include a key, header, manuscript text, request body, or hidden reasoning.

## Known limits

- There is no OCR. A fully image-only PDF fails before review.
- Very long PDFs fail if the complete paper is estimated not to fit the model context. ETS4 never silently shortens a paper.
- Raw responses are local files. Hosting would need per-user access, encryption, deletion jobs, and audit controls.
- Application URL checks are not enough for hosting; the network must also block private and cloud-metadata addresses.
- Cancellation stops later stages, but an already-running provider request may continue until timeout.
- `src/ets4/api/` contains data shapes only. There is no hosted service, login, upload system, or job queue.
- Valid structured output does not prove that a review is intellectually correct.
- The automated live test covers only Stage 1. The two full real-paper runs were manual and used prompt version `1.0.0`.

## Next recommended task

Finish Step 2 of [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): choose a licence, add maintainer and changelog details, use one version source, and review dependency and operating-system support. Then add a clean wheel and source-archive release test before any package-index publication.

The separate public website can be corrected at the same time. A hosted API, another provider, OCR, and formal human scoring remain optional until a concrete need appears.
