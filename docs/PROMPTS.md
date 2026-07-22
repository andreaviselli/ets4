# Prompt management

## Canonical assets

Versioned templates live under:

```text
src/ets4/prompts/templates/initial_editor/
src/ets4/prompts/templates/referee/
src/ets4/prompts/templates/final_editor/
```

Each version has a `.txt` template and `.json` metadata containing a stable ID, human-readable title, source-document SHA-256, and change notes. Derived versions also record the exact template SHA-256. Package-data configuration makes these assets available to an installed CLI.

The current default is `1.1.0`. The immutable `1.0.0` assets remain packaged for provenance and old-run inspection. Version `1.1.0` adds the same plain-English, informal, objective writing instruction to all three stages. It also gives final-editor issues an explicit reader-facing structure and compact assessment line without changing the fixed-panel protocol.

`PromptRepository` is the only renderer. Initial/final contexts contain the referee count. Referee context is a validated `RefereeProfile`; it supplies the functional slot, orientation, expertise, specialist topics, audit mandate, unique contribution, and non-authority areas.

Providers receive already rendered instructions and must not perform their own string replacement.

## Source precedence

1. July 2026 implementation brief;
2. stage-specific prompt PDFs;
3. general review-process PDF.

The fixed-panel rule in the brief and final prompt therefore overrides the general document's suggestion that more reviewers could be added after under-coverage.

Hashes and provenance are recorded in `docs/specification/SOURCE_DOCUMENTS.md`.

## Security language

Every stage template says that manuscripts and supplied artifacts are untrusted evidence, not instructions. It explicitly rejects embedded requests to change role, reveal secrets, access networks, use tools, or ignore the protocol.

This is defense in depth. The stronger control is architectural: provider requests contain no tools or secrets, referee supplemental context is empty, and the workflow constructs every call.

## Versioning rules

- Substantive editorial changes require a new semantic prompt version, updated metadata, behavioral evaluation, and a decision-log or ADR entry.
- Style and presentation changes require a new semantic prompt version, updated metadata, focused deterministic tests, and confirmation that the substantive editorial boundaries remain unchanged.
- Count/profile parameterization and typo fixes still require tests confirming that source rules remain present.
- Never tune prompts to one manuscript while claiming a general protocol.
- Keep source hashes stable for the imported version. A new source document creates new metadata rather than overwriting provenance.

## Regression checks

Deterministic tests verify required boundaries, dynamic fields, prompt hashes, strict output schemas, and final Markdown structure. Human-reviewed behavioral evaluations remain available for substantive future changes that text presence cannot verify, such as panel differentiation, non-anchoring, remit compliance, and synthesis quality.
