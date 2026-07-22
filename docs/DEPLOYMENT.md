# Deployment

## Supported setup: local package and CLI

Use Python 3.12 or later in a virtual environment. Keep keys in the process environment, local settings in the ignored `config/ets4.toml`, and confidential runs outside public or synchronized folders.

Install the package from a checkout:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install .
export OPENAI_API_KEY=...
ets4 validate-config --provider openai --model gpt-5.6
ets4 review manuscript.pdf --provider openai --model gpt-5.6
```

`python -m ets4` can replace `ets4`. The terminal process does the work. Provider calls stop after `request_timeout_seconds`, and a failed stage can be resumed.

ETS4 is not yet published on PyPI. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for the release checklist.

## Possible local container

A future container setup should mount one private input/output volume, add secrets only at runtime, run as a non-root user, limit CPU and memory, and allow network access only to the chosen provider and public manuscript hosts. Keys and manuscripts must never be built into the image.

## Hosted service: not built

The repository contains future API data shapes, not a working web service. Hosting would require:

- a background job queue and worker lifecycle;
- logged-in upload and status endpoints;
- private object storage and database state;
- locking so two workers cannot change one run at once;
- TLS, per-user access, quotas, and budgets;
- malware scanning and network rules that block private addresses;
- encryption, retention, deletion, and audit rules;
- health checks and operator instructions.

Do not keep one HTTP request open while all model calls run.

## Profiles

- Local test: mock provider, optional raw response retention, no network.
- Local OpenAI: environment key, private run directory, and explicit model settings.
- Hosted: future profile with raw retention off unless there is a clear reason and all privacy controls are in place.
