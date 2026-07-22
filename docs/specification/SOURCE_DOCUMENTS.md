# Source-document provenance

The July 2026 refactor used four user-supplied PDFs as the editorial source specification. The PDFs remain outside Git; their exact SHA-256 hashes preserve provenance without committing duplicate source files.

| Title | Pages | SHA-256 |
| --- | ---: | --- |
| ETS4 Review Process | 5 | `6b474d9664ce86ae36bf233915696fa23c4437815a91da027ee314d9ff7a45ce` |
| ETS4 Initial Editor Prompt | 2 | `37ebd396140235bdf45df17622fe5a2bb4c2d2af5726674ba2b9cd310e149350` |
| ETS4 Referee Prompt (Example) | 2 | `47f90a97eefe0255d04a30d99a7fc3290cfe3a32ab42afb0d1aa26f8897b8aa0` |
| ETS4 Final Editor Prompt | 3 | `c092ed843f1d3139f5956a90112e15540f82142455dd30c124b8e9f01fa4cc50` |

All pages were rendered and visually inspected in addition to text extraction. The general process PDF ends on page 5 with an incomplete source sentence. No missing continuation was inferred.

Specification precedence is:

1. `ETS4_Codex_Implementation_Prompt.md` supplied with the PDFs;
2. stage-specific prompt PDFs;
3. `ETS4 Review Process.pdf`.

Consequently, the fixed-panel final-editor rule overrides the general process document's exploratory suggestion that additional reviewers could be invited after observing coverage.

Canonical, parameterized prompt text is versioned under `src/ets4/prompts/templates/`. Metadata files repeat the source hash for the stage they normalize.
