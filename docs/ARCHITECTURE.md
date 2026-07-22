# Architecture

## System boundary

ETS4 is a local-first Python 3.12 library and CLI. It owns manuscript ingestion, editorial protocol prompts, structured outputs, model adapters, deterministic orchestration, durable artifacts, and Markdown rendering. It does not own the public website or publication workflow.

```text
CLI / future API contract
          |
          v
ReviewWorkflow (state, fan-out/fan-in, retries, resume)
   |          |             |                |
ingestion   prompts      providers         storage
   |          |             |                |
canonical   typed       mock / OpenAI     atomic JSON,
PDF + text  rendering   isolated calls    Markdown, logs
          \       |       /
           validated domain schemas
```

Dependencies point inward toward provider-neutral types. The workflow imports provider interfaces, never OpenAI SDK types. Prompt rendering occurs before provider calls and does not know API payload formats.

## Three-stage execution

1. Ingestion reads every PDF page, persists the canonical file and normalized page text, and calculates SHA-256.
2. Initial editor receives the complete manuscript and produces `EditorPanelDesign` for the configured count.
3. The orchestrator creates one isolated `StageRequest` per profile. Referee requests have empty supplemental context and receive only their rendered profile plus the complete manuscript.
4. Referee calls run in a bounded thread pool. Each validated report is atomically persisted as it completes.
5. Fan-in checks exact referee identifiers and count. Any missing report moves the run to `awaiting_retry`; the final editor is not called.
6. Final editor receives the complete manuscript, initial panel JSON, and every referee report JSON. It returns `FinalEditorDecision`.
7. The workflow verifies that every original coverage row and planned cell is preserved, renders Markdown, writes usage, and marks the run complete.

The same logical editor opens and closes the process through explicitly supplied Stage 1 artifacts. There is no hidden shared provider session.

## Durable state

`run-manifest.json` is the source of workflow status. The state sequence is:

```text
manuscript_received -> manuscript_normalized -> initial_editor_completed
-> referee_jobs_created -> referee_reports_in_progress
-> referee_reports_completed -> final_editor_completed
-> outputs_rendered -> completed
```

Any model-stage failure becomes `awaiting_retry`; explicit cancellation becomes `cancelled`. Outputs are written atomically before the manifest advances. Resume also discovers a valid stage JSON artifact if a process stopped after artifact persistence but before manifest persistence, avoiding a repeated paid call.

The deterministic input fingerprint hashes:

- manuscript SHA-256;
- prompt versions;
- structured-output schema hashes;
- provider runtime metadata, including the OpenAI SDK version when applicable;
- provider and model settings;
- referee count and behaviorally relevant run limits.

It supports run comparison and duplicate detection but does not imply byte-identical stochastic outputs.

## Provider boundary

`Provider` exposes:

- explicit capabilities;
- complete-manuscript preflight;
- one isolated structured `generate` call;
- retry classification;
- raw response, provider response ID, and usage metadata.

The OpenAI adapter uses the official SDK's `client.responses.parse`, Pydantic response types, and a base64 `input_file`. The mock adapter exercises the same orchestration without a network or cost.

Provider-facing structured schemas avoid dynamic-key objects because strict Structured Outputs require closed objects with explicit required properties. Coverage matrices therefore serialize as arrays of typed referee cells while domain validators still enforce exact referee identifiers. A local strict-schema compatibility check runs before every OpenAI request.

## Storage boundary

Run directories are intentionally simple and inspectable. JSON is authoritative for structured artifacts; Markdown is a deterministic human-readable view. Raw outputs are separate from public artifacts and controlled by retention settings.

There is no SQLite database or publishing-repository integration in the new system. Those were properties of the archived pre-refactor product.

## Optional API boundary

`src/ets4/api/contracts.py` contains only provider-independent DTOs. A future service should call the same workflow library asynchronously. HTTP, authentication, uploads, queues, and object storage must remain outside domain and provider modules.

## Consequential choices

See `docs/adr/` for the product replacement, application-controlled orchestration, OpenAI API primitives, and local persistence/retention decisions.
