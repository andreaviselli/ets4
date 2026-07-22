# Prompt management

## Source files

Versioned prompt files live in:

```text
src/ets4/prompts/templates/initial_editor/
src/ets4/prompts/templates/referee/
src/ets4/prompts/templates/final_editor/
```

Each version has a `.txt` template and `.json` metadata with a stable ID, title, source-document SHA-256, and change notes. Derived versions also record the template hash. Package settings include these files in built wheels.

The default is `1.1.0`. Version `1.0.0` stays packaged so old runs can be inspected. Version `1.1.0` asks all stages for plain, informal, objective writing and gives final issues a clearer reader-facing shape. It does not change the fixed-panel rules.

`PromptRepository` is the only renderer. It receives typed values such as panel size and referee profile. Providers receive finished instructions and must not edit prompt strings.

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
