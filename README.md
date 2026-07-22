# ETS4

ETS4 is an experimental, targeted academic-review system for manuscripts in economic time-series forecasting. It reads one complete manuscript, asks an initial editor to design a manuscript-specific artificial referee panel, runs the referees as operationally isolated model calls, and asks a final editor to synthesize the fixed panel into an editorial recommendation.

ETS4 complements human peer review. It does not replace a human editor, establish research correctness, publish a manuscript, search for external information about authors or papers, or expose manuscript-processing tools to review agents.

## Current interface

The reliable interface is a local terminal application. A run accepts either a local PDF or a narrowly resolvable manuscript URL and creates an isolated, resumable run directory.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Inspect the complete workflow without paid API calls:

```bash
ets4 review manuscript.pdf \
  --provider mock \
  --referees 4 \
  --output-dir ./runs
```

Run a substantive OpenAI-backed experiment:

```bash
export OPENAI_API_KEY=...
ets4 review manuscript.pdf \
  --provider openai \
  --model gpt-5.6 \
  --referees 4 \
  --output-dir ./runs
```

URL input uses the same command:

```bash
ets4 review https://example.org/manuscript.pdf --provider openai --model gpt-5.6
```

The mock provider proves orchestration only. Its synthetic reports and recommendation are not manuscript judgments.

## Configuration

Precedence is:

1. built-in safe defaults;
2. a TOML file supplied with `--config`;
3. `ETS4_*` environment variables;
4. command-line overrides.

Start from [`config/ets4.example.toml`](config/ets4.example.toml). API keys are accepted only through provider-standard server-side environment variables such as `OPENAI_API_KEY`; ETS4 deliberately has no API-key command-line option.

The default panel has four referees. `--referees` accepts a positive count up to the configured `max_referees` ceiling. The default ceiling is eight and the hard implementation limit is twelve.

Useful commands:

```bash
ets4 status RUN_ID --output-dir ./runs
ets4 resume RUN_ID --output-dir ./runs
ets4 cancel RUN_ID --output-dir ./runs
ets4 validate-config --config config/ets4.toml
ets4 providers
```

A partial provider failure exits with status 2 and leaves the run resumable. Successful paid stages are read from durable artifacts rather than repeated.

## Run artifacts

Each `runs/RUN_ID/` directory contains:

```text
run-manifest.json
manuscript.pdf
manuscript-metadata.json
manuscript-pages.json
initial-editor.json
initial-editor.md
referee-1.json
referee-1.md
...
final-editor.json
final-editor.md
usage.json
logs/events.jsonl
logs/raw/                 # when raw retention is enabled
```

The manifest records the manuscript hash and source, deterministic input fingerprint, non-secret configuration, prompt versions, model identifiers, state transitions, attempts, usage, failures, and artifact checksums. It never records an API key or hidden model reasoning.

## Manuscript handling and privacy

Manuscripts and reports may be confidential. Local runs copy the original PDF and extracted text into the selected output directory. Raw model responses are retained by default for local audit and can be disabled with `--no-retain-raw-responses`.

The OpenAI adapter sends the PDF inline to the Responses API, requests native PDF processing and validated Structured Outputs, supplies no model tools, and sets `store=false` by default. That setting does not eliminate all provider-side processing or abuse-monitoring retention. Review [`docs/DATA_AND_PRIVACY.md`](docs/DATA_AND_PRIVACY.md) before using confidential material.

## Manuscript input boundary

- Local inputs must be readable, unencrypted PDFs with extractable text.
- URL fetching allows only public HTTP(S) addresses on ports 80/443, validates every redirect, limits bytes and time, and resolves only a direct PDF, arXiv abstract page, `citation_pdf_url`, or explicit `application/pdf` link.
- ETS4 does not search for the paper, authors, reviews, publication status, publicity, or replication archives.
- The original PDF is canonical. Every page is normalized for validation and page mapping; no page is silently truncated.
- Scanned and unusually long PDFs can be supplied, but support is limited. A scan must already contain enough extractable text because ETS4 has no OCR; a fully image-only PDF fails before review.
- A long manuscript proceeds only if the complete-PDF preflight estimates that it fits the configured model context. ETS4 fails clearly rather than silently truncating the paper or substituting a summary.

## Architecture

The application, not a model, controls editor/referee ordering, fan-out/fan-in, retries, persistence, and final-editor release. Referees receive the complete manuscript and only their own rendered profile. They never receive other profiles, reports, or editor reasoning.

Prompt version `1.1.0` asks every editor and referee to write in plain English with an informal style while remaining objective. Final-editor issues are rendered as: where the issue applies, what is missing, why it matters, what needs to change, the editor's view, and one compact assessment line.

See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/REVIEW_PROTOCOL.md`](docs/REVIEW_PROTOCOL.md)
- [`docs/PROMPTS.md`](docs/PROMPTS.md)
- [`docs/PROVIDERS.md`](docs/PROVIDERS.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)
- [`docs/WEB_INTEGRATION.md`](docs/WEB_INTEGRATION.md)

## Development and validation

```bash
python -m pytest
python -m ruff check src tests evals
python -m mypy src/ets4 evals/build_case_pdf.py
python -m py_compile $(find src/ets4 evals -name '*.py' -type f | sort)
git diff --check
```

Live-provider tests are never part of the default suite. Behavioral editorial evaluations live under `evals/` and are distinct from deterministic schema and orchestration tests. The scaffold includes a fixed synthetic forecasting manuscript source, a reproducible PDF builder, behavioral probes, and a versioned human-scoring rubric.

Two local OpenAI-backed reviews of real manuscripts have completed the full initial-editor, four-referee, final-editor, and rendering workflow with `gpt-5.6`. These runs provide practical end-to-end validation of the current interface; they do not guarantee that every PDF will pass input and context checks or that every model judgment will be correct.

## Limitations

- LLM outputs remain stochastic; ETS4 records reproducibility inputs but does not promise byte-identical replay.
- Schema validity does not establish the intellectual quality of a review.
- The automated opt-in OpenAI smoke test covers only the initial-editor request. Full OpenAI workflows have also been run manually on two real manuscripts, but no formal behavioral-scoring exercise has been performed or is currently required.
- The service layer is an isolated contract skeleton, not a deployable hosted backend.
- Browser-side API keys are not implemented or recommended.
- HTML and PDF export can be added later; Markdown and JSON are the required formats now.
