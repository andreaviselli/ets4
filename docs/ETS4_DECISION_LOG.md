# ETS4 decision log

This log records durable architectural and editorial choices. The pre-July-2026 applied-digest decision history remains available through tag `archive/pre-targeted-review-2026-07-14`.

## 2026-07-14: replace the applied digest with targeted manuscript review

Decision: The active ETS4 product is the three-stage targeted manuscript-review system defined by the July 2026 implementation brief and prompt PDFs. The previous feed collection, triage, digest, benchmark, and export implementation is removed from the active package.

Context: The implementation brief explicitly declared the existing purpose unrelated and obsolete while requiring repository-history preservation.

Alternatives considered:

- add the manuscript-review engine beside the digest;
- create a separate package in the same repository;
- archive the prior commit and replace the active architecture.

Consequence: Commit `8d3be59` is preserved by archival tag, while the active CLI and docs describe only targeted manuscript review. Generic concepts were reimplemented only where they serve the new protocol.

Reversal condition: Restore from the archival tag or create a separately named product; do not merge the two editorial purposes into one ambiguous workflow.

## 2026-07-14: keep orchestration deterministic and application-controlled

Decision: Python workflow code controls all stage order, context construction, referee fan-out/fan-in, retry, validation, persistence, cancellation state, and final-editor release.

Context: Free-form model handoffs could expose reports across referees, run the final editor on partial input, or repeat paid calls after failure.

Alternatives considered:

- provider-hosted assistant threads;
- an agent SDK with model-directed handoffs;
- an explicit local state machine using stateless structured provider calls.

Consequence: Review agents receive no tools and cannot choose the next stage. Referees have separate requests with empty supplemental contexts. The final editor is released only after exact fixed-panel completion.

Reversal condition: A future workflow runtime may replace the file state machine only if it demonstrates the same inspectable context isolation, atomic idempotency, fixed-panel completeness, and provider independence.

## 2026-07-14: use Responses API, Structured Outputs, and inline native PDFs

Decision: The OpenAI adapter uses `client.responses.parse`, Pydantic Structured Outputs, and base64 PDF `input_file` content. `store=false` is the default and no tools are supplied.

Context: Official OpenAI documentation currently supports Pydantic parsing in the Responses API and describes PDF input as both text and page images on vision-capable models. Inline base64 avoids creating a separately durable Files API object.

Alternatives considered:

- Assistants API;
- plain JSON text plus local repair only;
- extracted text in place of the PDF;
- Files API upload IDs.

Consequence: Equations, tables, figures, and layout remain available to capable models while local extraction provides completeness checks and page mapping. The adapter remains isolated behind `Provider`.

Reversal condition: Revise the adapter and ADR if official SDK/API guidance, selected-model capability, retention behavior, or structured-output support changes.

## 2026-07-14: fixed panel coverage is diagnostic, not dynamic routing

Decision: Once Stage 1 creates the configured panel, the number of referees is fixed for the run. The final coverage appendix records under-coverage but does not add referees or change the manuscript recommendation merely because coverage was weak.

Context: The general process document contemplated additional reviewers, while the higher-precedence implementation brief and final-editor prompt explicitly forbid post-report referee additions.

Alternatives considered:

- dynamically add specialists for under-covered dimensions;
- ask the final editor to fill missing review dimensions;
- preserve the fixed panel and report coverage limitations.

Consequence: Runs are auditable, count-bounded, and comparable. Coverage failures inform later panel-design evaluation rather than mutating the current decision process.

Reversal condition: A separately versioned editorial protocol may introduce another review round with explicit human authorization; it must not be smuggled into the fixed-panel workflow.

## 2026-07-14: retain raw local responses by explicit policy

Decision: Local CLI runs retain raw provider responses by default for audit, separately under `logs/raw/`, with a configuration switch to disable retention.

Context: Auditability favors original-response preservation, while manuscript confidentiality requires explicit and documented retention behavior.

Alternatives considered:

- never retain raw responses;
- always retain without configuration;
- retain locally by default and require a distinct hosted retention policy.

Consequence: Users must protect and delete run directories appropriately. A hosted backend cannot inherit the local default without authentication, encryption, isolation, and lifecycle controls.

Reversal condition: Default to no raw retention if real users routinely process confidential manuscripts without suitable local controls, while keeping an explicit opt-in audit mode.

## 2026-07-14: close structured schemas and bind resume to schema/runtime provenance

Decision: Provider-facing coverage matrices use typed cell arrays rather than dynamic-key objects. Every OpenAI output object is locally checked for strict-schema compatibility before a request. New manifests and fingerprints record all stage schema hashes plus provider runtime metadata, and resume refuses schema or SDK drift.

Context: The first live initial-editor request reached OpenAI but failed with `invalid_json_schema` at `text.format.schema`. The SDK serialized `dict[str, CoverageLevel]` through schema-valued `additionalProperties`, which strict Structured Outputs rejected. The original run recorded prompt versions but no output-schema or SDK hash.

Alternatives considered:

- dynamically generate count-specific Pydantic object classes with aliased referee fields;
- bypass strict outputs and parse free-form JSON;
- use typed coverage cell arrays and retain exact-referee validation in the domain layer.

Consequence: The schemas are provider-compatible without coupling them to a configured panel size. Failures preserve sanitized server diagnostics. Runs started before schema provenance was recorded cannot be resumed across this repair and must be restarted; their prompt artifacts and failure logs remain auditable.

Reversal condition: A future provider may use another wire representation behind its adapter only if it maps losslessly to the same domain semantics, has explicit versioned provenance, and retains exact panel validation.

## 2026-07-22: prioritize documented local use and public-page accuracy

Decision: Treat the local OpenAI workflow as operational after two complete real-manuscript runs, update the public ETS4 description next, and defer formal human scoring, a second provider, and hosted execution until a concrete need arises.

Context: Two four-referee OpenAI runs completed every review stage and produced useful results for the user. The earlier roadmap incorrectly presented a human-scored exercise and provider expansion as mandatory gates before correcting the separate website.

Alternatives considered:

- keep formal behavioral scoring as the immediate milestone;
- require a second provider before continued use;
- build an interactive hosted service before updating the public page;
- document the working local system now and keep those expansions optional.

Consequence: The supported interface remains the local CLI. The website may be updated immediately as an informational page. Formal evaluation remains available for material prompt/model changes, and hosted security work remains mandatory only if browser-triggered reviews are pursued.

Reversal condition: Promote any deferred item when a specific requirement appears, such as image-only input, cross-provider operation, public review submission, or a material prompt/model change that needs comparative evaluation.

## 2026-07-22: make review writing informal and issue synthesis reader-facing

Decision: Release prompt version `1.1.0` with one shared instruction to write in plain English, avoid convoluted or unnecessarily technical language, and use an informal tone while remaining objective. Render each final-editor issue through six short reader-facing sections and one compact assessment line.

Context: The `1.0.0` final Markdown exposed schema fields as a checklist and listed referee reasoning separately. That layout was accurate but harder to read than a direct explanation of where an issue applies, what is missing, why it matters, what should change, and the editor's view.

Alternatives considered:

- change only the Markdown renderer without guiding the model;
- add detailed writing instructions to each referee comment;
- simplify the common writing instruction and structure only the final synthesis;
- replace structured issue metadata with free-form prose.

Consequence: The referee schema and substantive review protocol remain unchanged. `SynthesizedIssue` gains explicit fields for what is missing, why it matters, and what needs to change. Referee-specific reasoning remains in JSON for audit, while the Markdown view uses synthesized prose and compact metadata. The immutable `1.0.0` assets remain available.

Reversal condition: Revise the presentation in a later prompt version if the informal tone reduces precision, the section labels do not fit recurring issue types, or audit needs require selected referee attribution in the rendered report.
