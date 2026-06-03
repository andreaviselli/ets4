# ETS4

ETS4 is an editorial review system for economic time-series forecasting research.
Its immediate role is to collect candidate papers, review them with LLM-assisted
editorial workflows, and export draft pages for a separate publishing repository.

## Current State

The project currently contains:

- `ets4.py`: the active newsletter pipeline for RSS collection, LLM scoring, and Markdown export.
- `get_ets4.ipynb`: a notebook runner for the active pipeline.
- `deepdive_v3.ipynb`: a notebook workflow for full-paper deep dives.
- `deepdives/`: generated examples of deep-dive output.
- `old-deprecated/`: earlier experiments retained for reference.

## Repository Direction

The next development target is a reproducible, reviewable editorial system:

1. Structured paper collection from RSS and research sources.
2. Persistent paper/review storage.
3. Multi-stage editorial review.
4. Evaluation against labeled examples.
5. Draft export into the website repository with `draft: true`.
6. Human review before publication.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ROADMAP.md](docs/ROADMAP.md).

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
