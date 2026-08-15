# Prompt management

## Source files

Versioned prompt files live in:

```text
src/ets4/prompts/templates/initial_editor/
src/ets4/prompts/templates/requirement_discovery/
src/ets4/prompts/templates/referee/
src/ets4/prompts/templates/final_editor/
```

Each version has a `.txt` template and `.json` metadata with a stable ID, title, source-document SHA-256, and change notes. Derived versions also record the template hash. Package settings include these files in built wheels.

Default versions are recorded per stage. Requirement discovery uses `1.0.0`; panel design, referee, and final-editor prompts use `1.2.0`. Older prompt versions remain packaged for inspecting old runs.

Requirement discovery and panel design are separate so auto mode can avoid count anchoring. The discovery prompt asks for an importance-ordered list and receives an output schema with no item limit. The application cap is absent from both. Panel design then receives only the retained requirements and may not change them.

`PromptRepository` is the only renderer. It receives typed values such as exact-or-auto requirement mode, panel size, and referee profile. Providers receive finished instructions and must not edit prompt strings.

Referee `1.2.0` uses one prose field for each major comment, follows the manuscript's terminology and notation, requires a concrete example, and asks the referee to review each criticism a second time before finalizing it. Final-editor `1.2.0` uses one prose field of at most 2,000 characters per issue. Reader-facing Markdown hides audit classifications and uses the shorter Summary, Referee comments, and Recommendation sections.

External reference searches are not part of these prompts. They remain a possible future extension and would need a separate protocol and security decision before any tool is added to a review call.

## Source priority

1. July 2026 implementation brief;
2. stage-specific prompt PDFs;
3. general review-process PDF.

The brief and final-editor prompt fix the panel after Stage 1. That rule overrides the general document's suggestion that later coverage gaps might add reviewers.

Source hashes and priority are recorded in [`specification/SOURCE_DOCUMENTS.md`](specification/SOURCE_DOCUMENTS.md).

## Security rule

Every prompt says that manuscripts and supplied reports are untrusted evidence, not instructions. It rejects requests hidden in those files to change role, reveal secrets, use tools, or access a network.

The code provides the stronger protection: model requests include no tools or secrets, referee context contains only one profile, and the workflow builds every call.

## Changing a prompt

- A change to editorial meaning needs a new prompt version, updated metadata, human evaluation, and a decision-log or ADR entry.
- A style or layout change still needs a new version, focused tests, and a check that editorial boundaries did not move.
- New variables, count handling, and typo fixes need tests for the source rules they touch.
- Never tune a general prompt to one paper.
- Do not overwrite an old source hash. A new source document gets new metadata.

Tests check the required boundaries, variable fields, hashes, OpenAI-compatible output shapes, and final Markdown layout. Human evaluation remains available for questions that text checks cannot answer, such as panel quality and sound editorial judgment.
