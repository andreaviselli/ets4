# Architecture

## Project boundary

ETS4 is a local-first Python 3.12 package and command-line tool. It reads manuscripts, renders the review prompts, checks model output, controls the workflow, saves run files, and renders Markdown. It does not own the public website or publish papers.

```text
CLI / future API shapes
          |
          v
ReviewWorkflow (stage order, retries, resume)
   |          |             |                |
PDF input   prompts      providers         storage
   |          |             |                |
PDF + text  typed data   mock / OpenAI     JSON, Markdown,
                                            and event logs
          \       |       /
             checked models
```

The workflow depends on provider-independent Python types, not OpenAI SDK types. Prompts are rendered before a provider call, and prompt code does not build provider payloads.

## The three stages

1. PDF input reads every page, saves the original file and page text, and calculates its SHA-256 hash.
2. The initial editor receives the full manuscript and discovers an exact or unprompted number of ordered review requirements.
3. The application retains the requested set or, in auto mode, at most the first ten. It records a warning when it discards later requirements.
4. A separate panel-design call receives the full manuscript and only the retained requirements, then returns an `EditorPanelDesign` for the requested panel size.
5. The workflow creates one separate `StageRequest` for each referee. A referee receives the full manuscript and only their own profile.
6. Referees run in a limited thread pool. Each valid report is saved as soon as it finishes.
7. The workflow checks the expected referee IDs and total. If any report is missing, the run moves to `awaiting_retry` and the final editor stays blocked.
8. The final editor receives the full manuscript, the retained panel design, and every referee report. It returns a `FinalEditorDecision` whose reader-facing issues are prose passages capped at 2,000 characters; classifications and referee-specific reasoning remain structured audit data.
9. The workflow checks that the coverage table still contains every retained row and planned cell, writes Markdown and usage data, and completes the run.

The initial and final editor are the same logical role, linked by saved Stage 1 data. There is no hidden shared model conversation.

## Saved run state

`run-manifest.json` is the main record of progress:

```text
manuscript_received -> manuscript_normalized -> review_requirements_completed
-> initial_editor_completed
-> referee_jobs_created -> referee_reports_in_progress
-> referee_reports_completed -> final_editor_completed
-> outputs_rendered -> completed
```

A model failure becomes `awaiting_retry`; a user cancellation becomes `cancelled`. ETS4 finishes writing each output before it updates the manifest. On resume, it can recover a valid JSON output written just before a process stopped, so a paid call is not repeated.

The input fingerprint covers:

- the manuscript SHA-256;
- prompt versions;
- output-schema hashes;
- provider and SDK details;
- provider and model settings;
- panel size and limits that can affect results.
- exact or auto review-requirement mode and the application retention cap.

The fingerprint helps compare runs and spot duplicates. It does not mean that model output will be identical.

## Provider boundary

A provider reports its features, checks that it can handle the full manuscript, makes one separate structured call, classifies retryable errors, and returns usage and response details when available.

The OpenAI adapter uses `client.responses.parse`, Pydantic output models, and a base64 `input_file`. The mock adapter uses the same workflow without network access or cost.

OpenAI's strict output format does not allow open-ended object keys. Coverage tables therefore use arrays of typed referee cells, while local checks still require the exact referee IDs. ETS4 checks this format before each OpenAI request.

## Storage boundary

Each run is a normal directory that can be inspected or moved. JSON is the source for structured and audit data; Markdown is the simpler readable view and intentionally omits reviewer confidence, issue classifications, and referee-specific reasoning. Raw provider output is kept separately and only when the retention setting allows it.

The old digest product used SQLite and export folders. The current review package does not.

## Python package and future API

Installable code lives under `src/ets4/`. `ets4.cli` is the supported user interface, and `ets4.__main__` lets the same CLI run through `python -m ets4`.

`src/ets4/api/contracts.py` contains only data shapes for a possible future service. A hosted service should call the same workflow from background workers. Web routing, login, uploads, queues, and private storage must stay outside the review and provider modules.

See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for package-release work and [`adr/`](adr/) for the main design decisions.
