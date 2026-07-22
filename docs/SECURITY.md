# Security

## What ETS4 protects

Treat manuscript files and text, web pages, URLs, redirects, model output, filenames, run IDs, and config files as untrusted. Protect provider keys, confidential papers and reports, the host and its network, and the order of the review stages.

## Instructions hidden in a manuscript

Manuscript text is evidence, never an ETS4 instruction. Provider calls keep the PDF separate from ETS4's instructions, and every prompt repeats this rule. Review models receive no tools, browsing, shell, secrets, or unrelated app access.

Referees receive no extra files or data. The final editor receives only the checked panel and report JSON chosen by the workflow. Models cannot choose another agent or stage.

## URL fetching and SSRF

Server-side request forgery (SSRF) is an attempt to make ETS4 contact a private or unsafe network address. The PDF loader:

- allows only HTTP(S), ports 80 and 443, and URLs without credentials;
- rejects local names and private, loopback, link-local, multicast, reserved, or unspecified IP addresses;
- checks every redirect and any PDF link found on a landing page;
- handles redirects itself instead of following them automatically;
- limits time, redirects, and bytes;
- accepts only a direct PDF or a small set of explicit PDF links;
- never searches the web.

These application checks are not enough for a public multi-user service. Hosting also needs a proxy or firewall that blocks private and cloud-metadata addresses when the connection is made. Request logs must not expose keys or manuscripts.

## Files

- ETS4 checks the PDF header, parser result, encryption state, page count, and extracted text.
- It hashes and keeps the original bytes unchanged.
- It opens and reads every page. A page error stops the review.
- A fully image-only PDF fails instead of receiving a partial review.
- Run IDs and paths are limited to their run directory, and completed files are replaced safely.

A hosted upload service would also need malware scanning, its own file-type checks, quotas, and private storage separated by user.

## Secrets

- API keys come only from environment variables.
- Keys do not belong in CLI arguments, manifests, reports, normal logs, or errors.
- Provider errors are reduced to a small safe set of fields.
- Logs hide common API-key and Authorization patterns.
- `.env`, local config, and run output are ignored by Git.

## Cost and overload

ETS4 limits file size, PDF pages, referee count, parallel calls, context, output tokens, time, retries, and repair attempts. The default referee limit is eight; the hard code limit is twelve. A hosted service would also need login, user quotas, rate limits, budgets, and abuse monitoring.

## Cancellation

Cancellation is checked between stages and saved so the run cannot restart by accident. A provider request already in progress may continue until its timeout if the SDK cannot cancel it. Hosted workers must connect cancellation to both their job queue and provider client.

## Regression tests

Tests cover private redirects, broken files, separation of prompts from manuscript data, tool-free OpenAI requests, secret hiding, safe run paths, and partial failures.
