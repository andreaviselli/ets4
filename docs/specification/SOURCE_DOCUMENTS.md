# Source documents

The July 2026 rewrite used four user-supplied PDFs as the source for the review rules. The PDFs stay outside Git. Their SHA-256 hashes identify the exact files without committing copies.

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

The fixed-panel rule in the first two sources therefore overrides the general document's suggestion that coverage gaps could add reviewers.

The working, versioned prompt text lives under `src/ets4/prompts/templates/`. Each metadata file repeats the hash of its source PDF.
