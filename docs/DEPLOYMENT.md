# Deployment

## Supported foundation: local CLI

Use Python 3.12 or later in an isolated virtual environment. Keep keys in the process environment, config in an ignored TOML file, and run directories outside synchronized/public folders when manuscripts are confidential.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export OPENAI_API_KEY=...
ets4 validate-config --provider openai --model gpt-5.6
ets4 review manuscript.pdf --provider openai --model gpt-5.6
```

The terminal process is the worker. Long provider calls are bounded by `request_timeout_seconds`. A failed stage remains resumable.

## Containerized local worker

A later container profile should mount one private input/output volume, inject secrets at runtime, run as a non-root user, set memory/CPU limits, and deny network access except to the configured provider and user-supplied public manuscript hosts. Do not bake keys or manuscripts into images.

## Hosted service: not yet implemented

The API contracts are present, but a deployable service requires:

- asynchronous queue and worker lifecycle;
- authenticated upload and polling endpoints;
- private object storage and database state;
- process-level run locking and idempotency keys;
- TLS, tenant authorization, quotas, and budget limits;
- malware scanning and SSRF-resistant egress controls;
- encryption, retention, deletion, and audit policy;
- health monitoring and operator runbooks.

Holding one HTTP request open across all review calls is not an acceptable design.

## Configuration profiles

- Local test: mock provider, raw retention optional, no network.
- Local substantive: OpenAI provider, server-side environment key, private run directory.
- Hosted: future separate profile with raw retention off unless explicitly justified and all security controls implemented.
