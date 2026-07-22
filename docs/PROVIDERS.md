# Model providers

## Provider contract

A provider implements:

- explicit capability description;
- preflight against the complete normalized manuscript;
- one isolated structured generation call;
- retryability classification;
- response ID, raw response, and usage metadata when available.

The workflow does not import provider SDK types.

## Mock

`mock` is deterministic, offline, and free. It generates valid panels, reports, final synthesis, and coverage for orchestration tests. Its prose explicitly states that it is not a substantive manuscript assessment.

## OpenAI

`openai` is the first substantive adapter. It uses:

- the official Python SDK;
- Responses API `client.responses.parse`;
- Pydantic Structured Outputs;
- an inline base64 PDF `input_file` with configurable detail;
- the complete PDF in every stage call;
- `store=false` unless explicitly changed;
- no tools, web search, file search, shell, or code execution;
- explicit timeout and zero SDK-internal retries, leaving bounded retry to the orchestrator.
- a local strict-schema compatibility gate that rejects defaults, missing required fields, and dynamic-key objects before a paid request;
- sanitized API failure metadata (`message`, `code`, `parameter`, HTTP status, and request ID) without headers or request bodies.

Official references:

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Data controls](https://developers.openai.com/api/docs/guides/your-data)

The current official file-input guide says vision-capable models receive both extracted PDF text and page images. The structured-output guide documents Python Pydantic parsing through the Responses API. These are consequential external assumptions and are recorded in ADR 0003.

Live request validation on 2026-07-14 used OpenAI Python SDK `2.45.0` and `gpt-5.6`. It confirmed the documented inline PDF fields and exposed an invalid strict schema caused by dynamic-key coverage dictionaries. Coverage now uses typed cell arrays. The opt-in small-PDF initial-editor smoke test passes with the actual `EditorPanelDesign` schema. Separately, two manually launched reviews of real manuscripts completed the full three-stage OpenAI workflow with four referees. Those runs validate end-to-end operation for their inputs, not universal editorial quality.

Set credentials only in `OPENAI_API_KEY`. Model selection is configuration, not source code. Stage-specific overrides are available for the initial editor, referees, and final editor.

## Optional: adding another provider

A second provider is not required for current local OpenAI use. Add one only if cross-provider portability or a specific provider capability becomes a real project goal.

1. Implement `Provider` in a new `src/ets4/providers/<name>.py` module.
2. Declare native PDF, structured-output, text-fallback, reasoning, and storage-control capabilities accurately.
3. Reject incomplete-manuscript or unsupported-schema runs in `preflight` before cost.
4. Map only provider-specific transport and errors; return the same validated domain models.
5. Keep each `generate` call stateless and tool-free.
6. Add construction to the factory and capability listing.
7. Add mocked adapter tests plus the existing end-to-end workflow suite.
8. Document context windows, file support, retention, compatibility limits, and required environment variables.

Do not label an adapter "OpenAI-compatible" merely because it accepts a model name and key. Verify response format, file input, schema support, error types, timeouts, base URL semantics, and retention.

## Capability preflight

The current OpenAI adapter uses a conservative text-plus-page estimate against configured context and output limits. Future adapters should use maintained model-specific capability data. No adapter may silently truncate or replace the complete manuscript with a summary.
