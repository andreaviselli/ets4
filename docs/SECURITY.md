# Security

## Threat model

Untrusted inputs include manuscript bytes/text, landing pages, URLs, redirects, model outputs, supplemental artifacts, filenames, run identifiers, and configuration files. Protected assets include provider keys, confidential manuscripts, reports, host/network access, and workflow integrity.

## Prompt injection

Manuscript text never becomes system instructions. Each provider call separates the canonical PDF from ETS4 instructions, and every prompt reiterates the boundary. Review calls contain no tools, browsing, secrets, shell, or unrelated application functions.

Referees receive no supplemental artifacts. The final editor receives only explicitly serialized validated panel/report data. Models cannot choose another agent or stage.

## URL fetching and SSRF

The ingestor:

- permits only HTTP(S), ports 80/443, and no URL credentials;
- rejects local hostnames and private, loopback, link-local, multicast, reserved, or unspecified addresses;
- validates every redirect and resolved landing-page PDF;
- disables automatic redirects;
- applies time, redirect, and byte limits;
- accepts only a direct PDF or narrowly defined explicit PDF metadata/arXiv resolution;
- performs no web search.

Application validation alone is not sufficient for a hostile multi-tenant hosted service because DNS and network infrastructure differ. Hosted deployment must add an egress proxy or firewall that blocks internal/cloud-metadata ranges after resolution and at connection time, plus request logging that does not expose tokens or manuscripts.

## File handling

- PDF magic, parser readability, encryption, page count, and extracted text are validated.
- Original bytes are canonical and hashed.
- Every page is opened and extracted; a page exception fails the manuscript.
- Image-only inputs fail rather than receiving partial review.
- Paths and run IDs are constrained to run directories; writes are atomic.

A hosted upload path additionally needs malware scanning, content-type verification independent of user headers, quotas, and isolated object storage.

## Secrets

- API keys are environment-only.
- CLI arguments, manifests, outputs, normal logs, and errors contain no keys.
- Provider exception text is reduced to safe error classes.
- Logs redact common key and Authorization patterns.
- `.env`, local config, and run artifacts are ignored by Git.

## Denial of service and cost

File bytes, PDF pages, referee count, concurrency, context, output tokens, timeout, retry, and repair are bounded. The default referee ceiling is eight and the hard code ceiling is twelve. Hosted use also requires authentication, user quotas, rate limits, budget controls, and abuse monitoring.

## Cancellation

Cancellation is checked between stages and durably prevents resume. An in-flight HTTP request may continue until its provider timeout unless the adapter exposes a reliable cancellation primitive. Hosted workers must coordinate cancellation with their job queue and provider capabilities.

## Security regression tests

Tests cover private redirect rejection, invalid files, prompt/data separation, absence of tools in OpenAI requests, secret redaction, run-path constraints, and bounded partial-failure behavior.
