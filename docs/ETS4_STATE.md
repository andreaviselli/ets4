# ETS4 state

Last updated: 2026-07-22

## Current milestone

ETS4 has been refactored from the archived applied-forecasting digest into the targeted manuscript-review system specified by the July 2026 implementation brief and four supplied PDF source documents.

The former repository state is preserved at tag `archive/pre-targeted-review-2026-07-14` (commit `8d3be59`). Active implementation is on `codex/targeted-review-engine`.

The local review workflow is operational. Two OpenAI-backed reviews of user-supplied real manuscripts have completed the full initial-editor, four-referee, final-editor, and rendering sequence. The user reports that both results worked well for their intended use.

## Implemented foundation

- Local and remote manuscript PDF ingestion with content hashing, complete page-preserving text extraction, explicit unreadable/image-only failure, byte/page/time limits, constrained landing-page resolution, redirect validation, and SSRF checks.
- Provider-neutral manuscript package containing the canonical PDF, metadata, and paginated text.
- Versioned initial-editor, referee, and final-editor prompt templates with source hashes, typed contexts, count parameterization, manuscript prompt-injection boundaries, and a `1.1.0` plain-English, informal, objective writing instruction.
- Strict-compatible Pydantic schemas for panel design, harmonized referee reports, structured final-editor issue presentation, and planned-versus-realized typed coverage cells.
- Application-controlled durable state machine with isolated referee fan-out, configurable concurrency, bounded retry/repair, fan-in blocking, cancellation state, atomic artifacts, schema/runtime-bound input fingerprints, usage capture, and resume without repeating successful calls.
- Deterministic mock provider for complete no-cost local and test execution.
- OpenAI provider using the Responses API, Pydantic Structured Outputs, inline native PDF input, no model tools, explicit timeout, stage-specific model overrides, `store=false` by default, local strict-schema validation, and sanitized structured API diagnostics.
- CLI commands: `review`, `resume`, `status`, `cancel`, `validate-config`, and `providers`.
- JSON and Markdown run artifacts plus an isolated future service API contract.
- Deterministic tests for core ingestion, schema, prompt, provider, workflow, security, persistence, and CLI behavior.
- Versioned behavioral evaluation criteria plus a fixed synthetic forecasting manuscript, metadata, and reproducible PDF builder under `evals/`; live-provider evaluation is intentionally outside the default test suite.

## Current verification

Final implementation verification on Python 3.12.13:

- default `python -m pytest`: 46 passed and one opt-in live test skipped; only five third-party PyMuPDF SWIG deprecation warnings;
- opt-in `tests/test_live_openai_stage1.py`: passed against `gpt-5.6` with OpenAI SDK `2.45.0`, the production `EditorPanelDesign` schema, and a small synthetic PDF;
- `python -m ruff check src tests evals`: passed;
- `python -m mypy src/ets4 evals/build_case_pdf.py`: passed;
- exhaustive source and evaluation-script `py_compile`: passed;
- wheel build and package-content inspection: passed, including all versioned prompt assets;
- `git diff --check`: passed;
- tracked documentation/source local-path and secret-pattern scans: passed; only documented credential placeholders are present.

An end-to-end mock CLI smoke review of the generated three-page synthetic case completed all stages as `run-40d1d747c7a2`, with four isolated referee artifacts and input fingerprint `27e23a81cc8afdca092b1a8406557d8c31a922b457f9cfaff8d4102ad257f843`. The generated PDF was deterministic across two builds in this environment with SHA-256 `0fa4de1833db57fd71071163b6a9430e978a1147a45b941f1888d35b8e9d41e1`. Smoke outputs were written outside the repository.

Two local OpenAI runs on real manuscripts also completed every configured stage with four referees, `gpt-5.6`, prompt version `1.0.0`, and OpenAI SDK `2.45.0`: `run-0b756ca1200d` on 2026-07-14 and `run-f80d483ee1e0` on 2026-07-22. Their run manifests record `completed`, every expected stage, and no failed stages. This is practical end-to-end workflow evidence; it is not a claim that every manuscript or every model judgment will succeed.

After the `1.1.0` prompt and issue-presentation update, a fresh four-referee mock review completed all stages with the new prompt versions and schema hash. Its final Markdown rendered the six agreed issue sections and compact assessment line. A wheel build also included all `1.0.0` and `1.1.0` prompt text and metadata assets.

## Live adapter incident and recovery position

Run `run-746d588dcd6d` failed before Stage 1 output with OpenAI `BadRequestError`, status 400, code `invalid_json_schema`, parameter `text.format.schema`, and reproduced request ID `req_e85c08556ba742bdb67b7fd7a1fa8aad`. The exact server message and fields are now preserved in its event log and visible through `ets4 status`; no credential, header, manuscript content, request payload, or reasoning was logged.

The request's inline PDF encoding and fields match the official API form. The rejected schema used a dynamic-key coverage dictionary, which became schema-valued `additionalProperties`. It was replaced with strict-compatible typed coverage cells; output defaults were removed; and a regression gate rejects dynamic-key schemas locally before cost. At the time of that repair, the prompt templates remained at version `1.0.0` with no wording change.

The existing run must not be resumed. It predates structured-output schema hashes and OpenAI SDK provenance, and its Stage 1 request used the rejected schema. Current resume validation refuses it with `run structured-output schema provenance differs from this checkout; start a new run`. That failed run launched no referee calls; the two later runs listed above used the corrected schema and completed all four referee calls.

OpenAI SDK parsed-response serialization now explicitly disables Pydantic serializer warnings. This removes the SDK generic-union warning emitted after a successfully validated stage while preserving the raw response used by the configured local audit-retention path.

## Known limitations

- Automated live-test coverage stops after the initial editor, although two manually launched OpenAI reviews have completed the full workflow on real manuscripts.
- Scanned PDFs can be supplied, but ETS4 has no OCR and rejects a fully image-only manuscript that lacks sufficient extractable text.
- Very long PDFs can be supplied, but conservative context preflight rejects a complete manuscript estimated not to fit; ETS4 never silently truncates it.
- Raw response retention is local and file-based; hosted deployments require stronger per-user isolation, encryption, lifecycle jobs, and audit controls.
- URL defense is implemented in application code, but a hosted service must also enforce network-layer egress policy to close DNS-rebinding and infrastructure-specific gaps.
- Cancellation requests remain durable while a call is in flight and prevent subsequent stages. The already-running third-party HTTP request may finish because transport-level cancellation depends on provider SDK support and request timeout.
- The API package defines contracts only. There is no deployable asynchronous service, authentication, upload service, or job queue.
- Schema-valid output is not proof that every editorial judgment is correct. Formal human-scored behavioral evaluation remains available for future prompt or model changes but is deferred and is not the current next step.
- Prompt `1.1.0` changes writing style and final-report presentation while preserving the substantive protocol. Its deterministic prompt, schema, rendering, and workflow tests pass; the two completed real-manuscript runs used `1.0.0`.

## Next recommended task

Update the separate public website so that its ETS4 page describes the current targeted manuscript-review process and the local CLI accurately. This informational update does not require a hosted API.

Formal human-scored evaluation, a second provider adapter, OCR improvements, and a hosted asynchronous service are optional future work. Revisit them only if a concrete need arises, such as changing model/prompt behavior, supporting image-only manuscripts, validating cross-provider portability, or allowing website visitors to launch reviews.
