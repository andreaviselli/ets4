# ETS4

ETS4 is an editorial review system for applied economic forecasting research.
Its role is to collect candidate papers, run evidence-grounded editorial review,
evaluate reviewer quality, and export human-reviewable draft pages for a
practitioner/applied forecasting product in a separate publishing repository.

## Current State

The repository currently contains:

- `src/ets4/`: the active ETS4 package and CLI implementation.
- `docs/`: the target architecture, roadmap, review workflow, and evaluation design.
- `config/feeds.example.toml`: a starter source configuration.
- `data/` and `exports/`: ignored runtime working directories.

For project handoff and future agent work, start with:

- [docs/ETS4_STATE.md](docs/ETS4_STATE.md): current status, latest pilot state, known gaps, and next task.
- [docs/ETS4_DECISION_LOG.md](docs/ETS4_DECISION_LOG.md): durable architectural and editorial decisions.
- [AGENTS.md](AGENTS.md): operating rules for AI agents working on ETS4.

## Repository Direction

The target is a reproducible editorial system with these properties:

1. Papers and model outputs are stored as auditable structured records.
2. Reviews are grounded in cited source evidence, not free-form model impressions.
3. Editorial decisions pass through explicit gates before publication.
4. Prompt/model changes require evaluation against a labeled benchmark.
5. Draft pages are exported in review mode and remain unpublished until approved.

See:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/ETS4_STATE.md](docs/ETS4_STATE.md)
- [docs/ETS4_DECISION_LOG.md](docs/ETS4_DECISION_LOG.md)
- [docs/REVIEW_WORKFLOW.md](docs/REVIEW_WORKFLOW.md)
- [docs/EVALUATION.md](docs/EVALUATION.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/PILOT_VALIDATION.md](docs/PILOT_VALIDATION.md)
- [AGENTS.md](AGENTS.md)

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

The new package skeleton exposes an `ets4` command after installation.
Initialize the database and create a manifest first:

```bash
ets4 init-db
ets4 manifest --issue-date 2026-06-08
```

`manifest` prints a `run_id`. Later commands can continue the same auditable
run by passing `--run-id`:

```bash
ets4 collect --dry-run --run-id run-example123
ets4 triage --run-id run-example123
ets4 select --run-id run-example123
ets4 extract --run-id run-example123
ets4 refresh-evidence --run-id run-example123
ets4 review --run-id run-example123
ets4 benchmark-template --run-id run-example123
ets4 benchmark-status --labels path/to/benchmark.json
ets4 evaluate --run-id run-example123 --labels path/to/benchmark.json
ets4 replay-baseline --source-run-id run-example123 --labels path/to/benchmark.json --errors
ets4 export --run-id run-example123
ets4 archive --run-id run-example123
```

The default configuration is `config/feeds.example.toml`. Copy it to
`config/feeds.toml` for local changes; the local config file is ignored by Git.
Each `[[sources]]` entry controls one feed. For RSS sources, `lookback_days`
sets how far back ETS4 looks from collection time when filtering feed entries.
The example configuration currently uses 30 days for each starter source. Add
or remove source entries in `config/feeds.toml` to change pilot coverage.

The default model provider is `fake`, which is deterministic and suitable for
offline development and tests.

`triage` automatically applies the full-review paper budget after scoring
candidates. `select` can be run separately to recompute full-review selection
after configuration or human override changes.

`extract` retrieves documents for selected full-review papers and stores
page-preserving text plus evidence candidates. For one-off local review, pass an
explicit paper and document:

```bash
ets4 extract --paper-id paper-1 --source path/to/paper.pdf
```

`refresh-evidence` rebuilds evidence items from already stored extracted pages,
without refetching documents. Use it after evidence-kind rule changes to update
an ignored local pilot database before replay/evaluation.

`review` builds an evidence dossier from extracted evidence items, runs
independent fake reviewer reports for relevance, methods, evidence,
practitioner value, and transferability, then stores a handling-editor decision
memo. It also writes budgeted `deep_dive_draft` and `short_mention` selections
for human override before export. For one paper:

```bash
ets4 review --run-id run-example123 --paper-id paper-1
```

`benchmark-template` creates a human-labeling JSON template from a completed
run. By default it writes to `exports/benchmarks/{run_id}.benchmark-template.json`,
which is ignored by Git. The template is intentionally not evaluable until the
human editor fills the labels and sets each `label_status` to `accepted`.

`benchmark-status` validates benchmark JSON, reports labels that are still draft
or incomplete, emits accepted-label consistency warnings, and can write a
smaller copied subset for human editing. Add `--json` for a machine-readable
status and warning audit. It never fills labels or marks labels accepted.

`evaluate` compares a completed run against an accepted labeled benchmark JSON
file, stores aggregate and per-paper evaluation records in SQLite, and reports
core triage, evidence, review, and selection metrics. The test fixture at
`tests/fixtures/evaluation/benchmark.json` shows the expected label format.
Add `--errors` to list per-paper mismatches between human labels and ETS4
outputs and summarize failure types; `--json` includes the same error analysis
in machine-readable form.

`replay-baseline` creates a new evaluation-mode run from the papers triaged in
an existing source run, using the current configured provider and any stored
evidence already in SQLite. It does not recollect sources or publish artifacts.
Pass `--labels` to evaluate the replay run immediately.

`export` writes an issue-level draft page and companion internal notes under
`exports/{issue_id}/`. Exported public pages always include `draft: true`.
Generated files contain an ETS4 checksum marker, so reruns are idempotent and
human-edited files are not overwritten unless `--force` is passed.

`archive` creates a zip bundle containing the run manifest, run summary, and
exported artifacts. `run-scheduled` executes the non-publishing scheduled draft
pipeline and finishes by exporting and archiving:

```bash
ets4 run-scheduled --issue-date 2026-06-08
```
