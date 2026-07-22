# ADR 0003: OpenAI Responses API with native PDF and Structured Outputs

Status: accepted on 2026-07-14.

## Context

The implementation brief requires supported current OpenAI primitives, structured stage results, and visually meaningful PDF input. API assumptions are time-sensitive.

Official documentation consulted on 2026-07-14:

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Data controls](https://developers.openai.com/api/docs/guides/your-data)

The docs show Python `client.responses.parse` with Pydantic types and state that vision-capable PDF input processing includes extracted text and page images. They also document `input_file` base64 data and Responses storage controls.

## Decision

Use the official Python SDK Responses API, Pydantic `text_format`, inline base64 PDF `input_file`, configurable PDF detail, and `store=false` by default. Supply no tools. Keep local page text for completeness checks and provider-neutral packaging rather than silently replacing the PDF.

Strict output schemas must use closed objects with explicit required properties. Dynamic-key coverage maps are represented as arrays of typed `{referee_id, ...}` cells. Validate these constraints locally before sending a paid request. Record hashes for all three structured-output schemas and provider runtime metadata in new run manifests and fingerprints; refuse resume across schema or SDK provenance changes.

## Consequences

The adapter preserves PDF layout for capable models without creating a durable Files API object. Each stage uploads the complete PDF, increasing input cost but satisfying independent complete-manuscript access. Retention still depends on provider policies and organization controls.

The first live Stage 1 attempt on 2026-07-14, using SDK `2.45.0` and `gpt-5.6`, rejected `text.format.schema` with `invalid_json_schema`. The documented PDF fields, reasoning, output limit, and storage parameter were accepted far enough for schema validation. The cause was a Pydantic `dict[str, CoverageLevel]`, serialized as schema-valued `additionalProperties`, which is incompatible with strict Structured Outputs. After replacing dynamic maps and removing output defaults, the opt-in live Stage 1 smoke test succeeded. No referee or final-editor live calls were made.

## Reversal

Update this adapter and ADR if the official SDK/API, model file capability, structured-output support, or retention behavior changes. Never fall back silently to Assistants API or partial text.
