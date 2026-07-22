# Model providers

## Provider interface

A provider must:

- describe the features it supports;
- check the full manuscript before any paid call;
- make one separate call that returns checked structured data;
- say whether an error can be retried;
- return a response ID, raw response, and usage when available.

The workflow never imports provider SDK types.

## Mock

`mock` is repeatable, offline, and free. It creates valid panels, reports, final output, and coverage so the workflow can be tested. Its text clearly says it is not a real manuscript review.

## OpenAI

`openai` uses:

- the official Python SDK;
- the Responses API through `client.responses.parse`;
- Pydantic Structured Outputs;
- the complete PDF as an inline base64 `input_file`;
- `store=false` unless the user changes it;
- no tools, web search, file search, shell, or code execution;
- a set timeout and no hidden SDK retries;
- a local check that rejects unsupported output shapes before a paid request;
- short, secret-safe API error details.

Official references:

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Data controls](https://developers.openai.com/api/docs/guides/your-data)

The file guide says capable models receive both extracted PDF text and page images. The output guide describes Pydantic parsing through the Responses API. ADR 0003 records why ETS4 relies on these features.

A live check on 2026-07-14 used OpenAI SDK `2.45.0` and `gpt-5.6`. It found that open-ended coverage dictionaries were rejected by strict output validation, so ETS4 now sends typed cell arrays and checks them locally. The one-call Stage 1 smoke test passes. Two separate real-manuscript runs also completed all three stages with four referees. These runs prove the path worked for those inputs, not that every model judgment will be good.

Set credentials only in `OPENAI_API_KEY`. Models are settings, not hard-coded choices, and each stage can use its own model override.

## Adding another provider

Add a provider only when there is a real need for another service or feature.

1. Implement `Provider` in `src/ets4/providers/<name>.py`.
2. Describe PDF, structured-output, text fallback, reasoning, and storage controls accurately.
3. Reject unsupported full manuscripts or output formats before cost.
4. Keep transport and error handling inside the adapter; return the shared ETS4 models.
5. Keep every call separate and tool-free.
6. Add it to the factory and provider list.
7. Add mocked adapter tests and run the full mock workflow tests.
8. Document context limits, PDF support, retention, compatibility, and environment variables.

Do not call an adapter “OpenAI-compatible” based only on a model name and key. Check its response format, PDF input, strict output support, errors, timeouts, base URL, and retention.

## Full-manuscript check

The OpenAI adapter makes a cautious estimate for PDF text and pages, then compares it with the configured context and output limits. Future adapters should keep model-specific limits current. No provider may silently shorten the paper or replace it with a summary.
