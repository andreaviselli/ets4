# ADR 0003: OpenAI Responses with PDFs and structured output

Status: accepted on 2026-07-14.

## Context

ETS4 needs current supported OpenAI features, checked stage output, and access to PDF layout. These API details can change.

Official docs checked on 2026-07-14:

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Data controls](https://developers.openai.com/api/docs/guides/your-data)

They describe Python Pydantic parsing, base64 PDF input, extracted PDF text and page images for capable models, and Responses storage controls.

## Decision

Use the official Python SDK, `client.responses.parse`, Pydantic `text_format`, an inline base64 `input_file`, configurable PDF detail, and `store=false` by default. Give the model no tools. Keep local page text to check completeness and map pages; do not replace the PDF with it.

Strict output objects must list every allowed field. Coverage uses arrays of `{referee_id, ...}` cells instead of arbitrary object keys. Check these rules before a paid request. Record hashes for all three output shapes plus provider and SDK versions, and refuse resume across incompatible changes.

## Result

Capable models can inspect the PDF layout without a separate Files API object. Every stage sends the full PDF, which costs more input tokens but preserves referee independence. Provider retention rules still apply.

The first live Stage 1 request failed because `dict[str, CoverageLevel]` produced an unsupported `additionalProperties` schema. Typed cell arrays and removal of defaults fixed it, and the one-call live smoke test then passed.

## Revisit if

The SDK, API, model PDF support, output rules, or retention terms change. Never fall back silently to a retired API or partial text.
