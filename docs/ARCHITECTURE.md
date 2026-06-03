# ETS4 Architecture

ETS4 is an evidence-grounded editorial review engine for economic time-series
forecasting research. It should not be designed as a newsletter script. The core
product is a reproducible review system that can explain why a paper was
selected, what evidence supports the selection, where the assessment is weak,
and whether the review process is improving over time.

## Product Boundary

ETS4 owns:

- source discovery and metadata normalization
- paper/full-text acquisition
- evidence extraction
- multi-stage editorial review
- evaluation and regression testing of review quality
- draft generation and export

ETS4 does not own:

- final website rendering
- publication approval
- manual editorial corrections
- claims that cannot be traced to source evidence

The publishing site should be treated as a downstream target. ETS4 may export a
draft page, but it must never silently publish or flip a page out of draft mode.

## Architecture Principles

1. **Evidence before prose.** Summaries should be generated only after the system
   has extracted source-backed claims, methods, data, metrics, limitations, and
   uncertainty flags.
2. **Review before generation.** Draft pages are downstream artifacts. The
   durable product is the structured review record.
3. **Evaluation gates model changes.** Prompts, models, retrieval logic, and
   reviewer rubrics should not change production behavior without benchmark
   comparison.
4. **Provider abstraction.** LLM calls should sit behind a model interface so the
   project can compare OpenAI, local, and other hosted models without rewriting
   workflows.
5. **Human-in-the-loop by design.** The system should produce editor questions,
   confidence flags, and unresolved issues rather than pretending full
   automation is sufficient.
6. **Deterministic core, probabilistic edge.** Fetching, parsing, deduplication,
   storage, scoring schemas, and exports should be deterministic and tested.
   LLM outputs should be structured, validated, and versioned.

## Target Pipeline

1. Collect candidate papers from configured sources.
2. Normalize metadata and deduplicate by DOI, arXiv id, canonical URL, and fuzzy title.
3. Store every candidate paper before model review.
4. Run cheap triage on title, abstract, source, and metadata.
5. Fetch full text only for plausible candidates.
6. Extract evidence spans, figures, tables, datasets, metrics, baselines, and code links.
7. Run specialist reviews against structured rubrics.
8. Reconcile disagreement and produce an editorial decision.
9. Generate public draft plus internal review notes.
10. Export to a configured publishing repository with `draft: true`.

## Core Components

### Source Registry

Configured feeds and APIs live outside code. Each source should define its name,
type, URL, expected quality, polling cadence, and parser hints. Hard-coded source
lists in notebooks are obsolete.

### Paper Store

Use SQLite first. It is sufficient for a single-editor workflow, inspectable, and
easy to back up. Store papers, source events, extracted documents, evidence
items, review runs, reviewer outputs, decisions, exports, and evaluation labels.

### Document Processor

The processor should retrieve abstracts and full text, convert PDFs to structured
page text, preserve page numbers, and extract tables/figures when possible.
Every extracted evidence item should retain a source locator.

### Review Orchestrator

The orchestrator runs role-specific reviewers and writes structured JSON. It
should support retries, schema validation, model/version logging, temperature
control, and deterministic replay where possible.

### Evaluation Harness

Evaluation is not optional. It should run on labeled paper sets and compare
reviewer versions before deployment. See `docs/EVALUATION.md`.

### Draft Exporter

The exporter converts approved review records into Markdown plus a companion
editorial-notes file. Export should be idempotent and should never overwrite
manual edits unless explicitly requested.

## Proposed Repository Layout

```text
ets4.py                  # legacy prototype retained until migrated
config/
  feeds.example.toml     # source registry example
data/                    # local SQLite/cache files, ignored except .gitkeep
docs/
  ARCHITECTURE.md
  EVALUATION.md
  REVIEW_WORKFLOW.md
  ROADMAP.md
exports/                 # generated drafts, ignored except .gitkeep
pyproject.toml
README.md
```

Future code should move from `ets4.py` into a package layout:

```text
src/ets4/
  cli.py
  config.py
  collect/
  documents/
  review/
  evaluate/
  export/
  store/
tests/
```

## Non-Goals

- No autonomous publishing.
- No ungrounded summaries.
- No production logic in notebooks.
- No one-shot relevance scoring as the final editorial decision.
- No prompt changes without evaluation.
