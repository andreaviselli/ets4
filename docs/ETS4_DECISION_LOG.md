# ETS4 decision log

This file records choices that should survive day-to-day code changes. The old applied-digest decisions remain in Git under tag `archive/pre-targeted-review-2026-07-14`.

## 2026-07-14: replace the applied digest with manuscript review

Decision: ETS4 is now the three-stage paper-review system defined by the July 2026 brief and prompt PDFs. The old feed, sorting, digest, benchmark, and export code is no longer part of the active package.

Why: The brief said the old purpose was unrelated and should be replaced, while keeping its history.

Options considered:

- keep both products in one package;
- create another package in this repository;
- tag the old version and give ETS4 one clear purpose.

Result: Commit `8d3be59` is protected by the archive tag. Current code and docs describe only manuscript review.

Revisit if: The digest is needed again. Restore or fork it from the tag instead of mixing both products.

## 2026-07-14: let Python control the workflow

Decision: Python code controls stage order, referee contexts, parallel calls, retries, checks, saved files, cancellation, and final-editor release.

Why: Free-form model handoffs could expose one referee's work to another, start the final editor too early, or repeat paid calls after failure.

Options considered:

- provider-hosted assistant threads;
- model-directed agent handoffs;
- a clear local state machine with separate structured calls.

Result: Review models receive no tools and cannot choose the next step. Each referee gets a separate request. The final editor starts only when the fixed panel is complete.

Revisit if: Another workflow system can prove the same context separation, safe file writes, resume behavior, fixed-panel checks, and provider independence.

## 2026-07-14: use Responses, structured output, and inline PDFs

Decision: The OpenAI adapter uses `client.responses.parse`, Pydantic output models, and a base64 PDF `input_file`. It sets `store=false` by default and gives the model no tools.

Why: Official OpenAI docs support Pydantic parsing and say capable models can receive PDF text and page images. Inline data avoids creating a separate Files API object.

Options considered:

- Assistants API;
- plain JSON text checked only after the call;
- extracted text instead of the PDF;
- Files API uploads.

Result: Models can inspect equations, tables, figures, and layout. Local text extraction still checks completeness and page mapping. Provider-specific code stays behind `Provider`.

Revisit if: The SDK, API, chosen model, file handling, output format, or retention rules change.

## 2026-07-14: keep the panel fixed after Stage 1

Decision: Once Stage 1 creates the panel, its size stays fixed for that run. The final appendix can report missed coverage but cannot add referees or change the paper recommendation just because coverage was weak.

Why: The general process document mentioned later reviewers, but the higher-priority brief and final-editor prompt forbid them.

Options considered:

- add specialists when a gap appears;
- ask the final editor to fill missing review areas;
- keep the panel fixed and report its limits.

Result: Runs have clear costs and can be compared. Coverage gaps help improve later panel design rather than changing the current review.

Revisit if: A new, clearly versioned protocol adds another round with human approval.

## 2026-07-14: keep raw local responses by default

Decision: Local runs keep raw provider responses under `logs/raw/` unless the user turns this off.

Why: Original responses help auditing, but papers may be confidential and retention must be visible.

Options considered:

- never keep raw responses;
- always keep them;
- keep them by default only for local runs and require a separate hosting policy.

Result: Users must protect and delete run directories. A hosted service cannot copy this default without login, encryption, user separation, and deletion rules.

Revisit if: Real users often handle confidential papers without suitable local controls. In that case, default to no raw retention and keep an explicit opt-in audit mode.

## 2026-07-14: use closed output shapes and bind resume to versions

Decision: Coverage data uses typed cell arrays, not objects with arbitrary keys. ETS4 checks every OpenAI output shape before a request. Manifests record output-schema hashes and provider runtime details, and resume refuses incompatible changes.

Why: The first live initial-editor request failed with `invalid_json_schema`. A Pydantic `dict[str, CoverageLevel]` produced an `additionalProperties` shape that strict Structured Outputs rejected. The old run did not record enough schema or SDK detail for safe resume.

Options considered:

- create a new Pydantic class for every panel size;
- parse free-form JSON;
- use cell arrays and check exact referee IDs locally.

Result: One output shape works for every supported panel size. Safe error details are saved. Runs created before the added version data must restart.

Revisit if: Another provider needs a different wire format that maps exactly to the same ETS4 data and records its own version details.

## 2026-07-22: document local use before expanding the product

Decision: Treat the local OpenAI workflow as working after two complete real-paper runs. Correct the public description next, while leaving formal human scoring, another provider, and hosting as optional work.

Why: Both four-referee runs completed and were useful to the user. The old roadmap made optional expansion look like a gate before simple documentation work.

Options considered:

- require formal scoring next;
- require another provider;
- build hosting before correcting the site;
- document the working local tool now.

Result: The local CLI remains the supported interface. Formal evaluation is still available when a prompt or model changes, and hosting security remains mandatory if public submissions are added.

Revisit if: A concrete need appears, such as image-only papers, another provider, public submissions, or an important prompt change.

## 2026-07-22: make reports easier to read

Decision: Prompt version `1.1.0` asks for plain English and an informal but objective tone. Final issues use six short reader-facing sections and one compact assessment line.

Why: Version `1.0.0` exposed output fields as a checklist and separated referee reasoning. It was accurate but harder to read.

Options considered:

- change only Markdown rendering;
- add detailed style rules to every comment;
- use one simple shared style rule and structure only the final report;
- replace checked issue data with free-form prose.

Result: The referee format and review rules stay the same. JSON keeps referee-specific reasoning for audit, while Markdown presents one clear explanation per issue. Version `1.0.0` remains available.

Revisit if: The tone reduces precision, the section labels fit poorly, or audit needs require referee names in the readable report.

## 2026-07-22: prepare a staged Python package release

Decision: Keep installation from a repository checkout as the supported path while preparing a proper public package release. Support both `ets4` and `python -m ets4`, test built files in a clean environment, and do not claim PyPI availability before a licence and release process are in place.

Why: The repository already builds a wheel, but the README only showed an editable developer install and there was no release checklist. Publishing immediately would leave ownership, licence, metadata, and clean-install checks unresolved.

Options considered:

- keep the developer-only install instructions;
- publish the current wheel immediately;
- improve local package use now and release only after the checklist passes.

Result: User and developer install steps are separate, package metadata is clearer, and [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) holds the remaining release work.

Revisit if: The package is published or the project remains private. Update the install path and remove release steps that no longer apply.
