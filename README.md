# ETS4

ETS4 is an editorial review system for economic time-series forecasting research.
Its role is to collect candidate papers, run evidence-grounded editorial review,
evaluate reviewer quality, and export human-reviewable draft pages for a separate
publishing repository.

## Current State

The repository currently contains:

- `src/ets4/legacy.py`: the legacy prototype for RSS collection, LLM scoring, and Markdown export.
- `docs/`: the target architecture, roadmap, review workflow, and evaluation design.
- `config/feeds.example.toml`: a starter source configuration.
- `data/` and `exports/`: ignored runtime working directories.

## Repository Direction

The target is a reproducible editorial system with these properties:

1. Papers and model outputs are stored as auditable structured records.
2. Reviews are grounded in cited source evidence, not free-form model impressions.
3. Editorial decisions pass through explicit gates before publication.
4. Prompt/model changes require evaluation against a labeled benchmark.
5. Draft pages are exported in review mode and remain unpublished until approved.

See:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/REVIEW_WORKFLOW.md](docs/REVIEW_WORKFLOW.md)
- [docs/EVALUATION.md](docs/EVALUATION.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,deepdive]"
```

Create a local `.env` file containing:

```bash
OPENAI_API_KEY=...
```

`.env` is ignored by Git.

## Phase 1 CLI

The new package skeleton exposes an `ets4` command after installation:

```bash
ets4 init-db
ets4 manifest --issue-date 2026-06-08
ets4 collect --dry-run --issue-date 2026-06-08
ets4 triage --issue-date 2026-06-08
```

`manifest` prints a `run_id`. Later commands can continue the same auditable
run by passing `--run-id`:

```bash
ets4 collect --dry-run --run-id run-example123
ets4 triage --run-id run-example123
```

The default configuration is `config/feeds.example.toml`. Copy it to
`config/feeds.toml` for local changes; the local config file is ignored by Git.

The default model provider is `fake`, which is deterministic and suitable for
offline development and tests.
