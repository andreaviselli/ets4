# ETS4

ETS4 is an experimental AI review tool for economic time-series forecasting papers. It reads one complete manuscript, builds a paper-specific referee panel, runs each referee separately, and produces an editor's final report.

ETS4 supports human peer review. It does not replace an editor or prove that a paper is correct.

## How the review works

1. The initial editor identifies five to eight main review needs and designs the requested referee panel.
2. Each referee receives the full PDF and only their own profile. Referees cannot see one another's profiles or reports.
3. The final editor runs only after every referee report has been checked and saved. It combines the issues, makes a recommendation, and compares planned with actual coverage.

The Python workflow controls the order, retries, saved files, and referee separation. The models do not choose the next step or call tools.

## Install from this repository

ETS4 needs Python 3.12 or later. It is not yet published on PyPI. To install it directly from GitHub:

```bash
python -m pip install "git+https://github.com/andreaviselli/ets4.git"
```

In Jupyter or IPython, use the kernel's `%pip` command, then restart the kernel if the imports are not immediately available:

```python
%pip install "git+https://github.com/andreaviselli/ets4.git"
```

You can instead clone the repository and install the local checkout:

```bash
git clone https://github.com/andreaviselli/ets4.git
cd ets4
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

This installs the `ets4` command. You can also use `python -m ets4`.

For development, install the project in editable mode with its test tools:

```bash
python -m pip install -e ".[dev]"
```

The package and release work still needed before a public release is listed in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## Use ETS4 from Python

Start with the free mock provider. It runs the complete workflow but produces test reports rather than real manuscript judgments:

```python
from pathlib import Path

from ets4.config import ReviewSettings
from ets4.providers.factory import build_provider
from ets4.workflow import ReviewWorkflow

settings = ReviewSettings(
    provider="mock",
    referee_count=4,
    output_dir=Path("runs"),
)

workflow = ReviewWorkflow(settings, build_provider(settings))
result = workflow.start("manuscript.pdf")

print(result.run_id)
print(result.workflow_state.value)
print(settings.output_dir / result.run_id / "final-editor.md")
```

For a real OpenAI review, set `OPENAI_API_KEY` in the environment before starting Python. Then use OpenAI settings with the same workflow:

```python
from pathlib import Path

from ets4.config import ReviewSettings, validate_provider_environment
from ets4.providers.factory import build_provider
from ets4.workflow import ReviewWorkflow

settings = ReviewSettings(
    provider="openai",
    model="gpt-5.6",
    referee_count=4,
    output_dir=Path("runs"),
)

validate_provider_environment(settings)
result = ReviewWorkflow(settings, build_provider(settings)).start("manuscript.pdf")

print(result.run_id)
print(result.workflow_state.value)
```

A supported manuscript URL can replace `"manuscript.pdf"` in either example.

## Try the workflow for free

The mock provider checks the full workflow without API calls:

```bash
ets4 review manuscript.pdf \
  --provider mock \
  --referees 4 \
  --output-dir ./runs
```

Its reports are test data, not real judgments about the manuscript.

## Run an OpenAI review

Keep the API key in the process environment:

```bash
export OPENAI_API_KEY=...
ets4 review manuscript.pdf \
  --provider openai \
  --model gpt-5.6 \
  --referees 4 \
  --output-dir ./runs
```

A supported URL can replace the local path:

```bash
ets4 review https://example.org/manuscript.pdf --provider openai --model gpt-5.6
```

Useful commands:

```bash
ets4 status RUN_ID --output-dir ./runs
ets4 resume RUN_ID --output-dir ./runs
ets4 cancel RUN_ID --output-dir ./runs
ets4 validate-config --config config/ets4.toml
ets4 providers
```

A partial provider failure exits with status 2 and leaves the run ready to resume. ETS4 reuses completed stages instead of paying for them again.

## Configuration

Settings are applied in this order:

1. safe built-in defaults;
2. a TOML file passed with `--config`;
3. `ETS4_*` environment variables;
4. command-line options.

Copy [`config/ets4.example.toml`](config/ets4.example.toml) to the ignored path `config/ets4.toml` if you want a local config file. ETS4 accepts API keys only through provider environment variables such as `OPENAI_API_KEY`; there is no API-key command-line option.

The default panel has four referees. `--referees` accepts a positive number up to `max_referees`. The default limit is eight and the hard limit is twelve.

## Run files

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
logs/raw/                 # only populated when raw retention is enabled
```

The manifest records the manuscript hash and source, non-secret settings, prompt and model versions, stage progress, attempts, usage, failures, and file checksums. It never records an API key or hidden model reasoning.

## Manuscripts and privacy

Manuscripts and reports may be confidential. Local runs copy the PDF and extracted text into the chosen output directory. Raw model responses are kept by default for local auditing; use `--no-retain-raw-responses` to disable that.

The OpenAI adapter sends the PDF inline to the Responses API, asks for structured output, gives the model no tools, and sets `store=false` by default. This does not rule out all provider-side processing or safety retention. Read [`docs/DATA_AND_PRIVACY.md`](docs/DATA_AND_PRIVACY.md) before using confidential material.

Input rules:

- Local files must be readable, unencrypted PDFs with enough extractable text.
- URL fetching accepts only public HTTP(S) addresses on ports 80 and 443. Every redirect is checked, and download size and time are limited.
- ETS4 accepts a direct PDF, an arXiv abstract page, `citation_pdf_url`, or an explicit `application/pdf` link. It does not search for papers.
- The original PDF is kept unchanged. Every page is read; ETS4 never silently shortens the paper or replaces it with a summary.
- There is no OCR. A fully image-only PDF fails before review.
- A long paper proceeds only when the full PDF is estimated to fit the configured model context.

## Documentation

Start with the [`docs` guide](docs/README.md). The main references are:

- [`docs/REVIEW_PROTOCOL.md`](docs/REVIEW_PROTOCOL.md) — what each review stage may do;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the code and saved state fit together;
- [`docs/SECURITY.md`](docs/SECURITY.md) — trust boundaries and URL/file controls;
- [`docs/PROMPTS.md`](docs/PROMPTS.md) — prompt versions and change rules;
- [`docs/PROVIDERS.md`](docs/PROVIDERS.md) — mock and OpenAI adapters;
- [`docs/ETS4_STATE.md`](docs/ETS4_STATE.md) — current status and known limits.

The public website lives in the separate `andreaviselli.github.io` repository.

## Development checks

```bash
python -m pytest
python -m ruff check src tests evals
python -m mypy src/ets4 evals/build_case_pdf.py
python -m py_compile $(find src/ets4 evals -name '*.py' -type f | sort)
git diff --check
```

Live provider tests are optional and off by default. The `evals/` directory contains a fixed synthetic paper and a human scoring guide; it is separate from the normal test suite.

## Current limits

- Model output varies between runs. Recorded settings help comparison but do not promise identical output.
- Valid JSON does not prove that a review is intellectually sound.
- The automated live test covers only the initial editor. Two full OpenAI reviews have also completed manually, but that does not guarantee success for every PDF or judgment.
- `src/ets4/api/` contains future API shapes only. There is no hosted service, login, upload system, or job queue.
- Markdown and JSON are the supported report formats.
