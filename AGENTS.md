# AGENTS

This file is the operating guide for AI agents working on ETS4.

## Read First

Before making changes, read these files in order:

1. `README.md`
2. `docs/ETS4_STATE.md`
3. `docs/ROADMAP.md`
4. `docs/PILOT_VALIDATION.md`
5. `docs/REVIEW_WORKFLOW.md`
6. `docs/EVALUATION.md`
7. `docs/ETS4_DECISION_LOG.md`

For narrow implementation tasks, read the relevant source and tests after the
handoff docs.

## Current Project Posture

Read `docs/ETS4_STATE.md` for the current milestone, latest run state, known
gaps, and next recommended task. Treat that file as the mutable project
handoff; treat this file as durable operating policy.

Follow the current milestone unless the human editor explicitly changes
direction. When direction changes, update `docs/ETS4_STATE.md` and add a
decision-log entry if the change affects architecture, editorial policy, model
selection, evaluation gates, or publication workflow.

## Non-Negotiable Constraints

- Do not commit runtime outputs from `data/` or `exports/`.
- Do not commit local SQLite databases, archives, secrets, `.env`, or
  `config/feeds.toml`.
- Do not add local machine paths to tracked files.
- Do not treat generated benchmark templates as gold labels.
- Do not run `ets4 evaluate` on labels unless human-reviewed labels are marked
  `label_status: "accepted"`.
- Do not publish or push generated website content without explicit human
  approval.
- Keep deterministic baselines available when comparing model or workflow
  changes.
- Do not adopt real model providers, website integration, or publication
  automation without either satisfying the relevant evaluation/publication gate
  or recording explicit human approval in the decision log.

## Implementation Standards

- Prefer existing package structure under `src/ets4/`.
- Keep CLI behavior reproducible through SQLite records and run manifests.
- Store evidence separately from review prose.
- Make failures explicit and recoverable.
- Add focused tests for new behavior.
- Keep docs synchronized with workflow changes.
- Update `docs/ETS4_STATE.md` after substantive changes.
- Add a `docs/ETS4_DECISION_LOG.md` entry for architectural or editorial
  decisions that affect future direction.

## Verification Before Commit

Run:

```bash
python -m pytest
python -m ruff check src tests
python -m py_compile src/ets4/*.py src/ets4/store/*.py src/ets4/collect/*.py src/ets4/documents/*.py src/ets4/review/*.py src/ets4/evaluate/*.py src/ets4/export/*.py src/ets4/ops/*.py
```

Also check:

```bash
git diff --check
```

Also scan tracked docs and source files for absolute local machine paths before
committing.

## Git Hygiene

- Work on scoped changes.
- Do not revert user changes unless explicitly asked.
- Stage only relevant files.
- Prefer concise commits that match one logical task.
- If committing and pushing, verify the working tree is clean afterward.

## Handoff Practice

When a task changes project status, update `docs/ETS4_STATE.md` with:

- what changed
- latest relevant run ids or generated artifacts
- current pilot-validation position
- known failures
- next recommended task

When a task changes direction or policy, add a decision-log entry with:

- decision
- context
- alternatives considered
- consequence
- reversal condition
