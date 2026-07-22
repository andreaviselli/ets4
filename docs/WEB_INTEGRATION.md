# Website options

The public page lives in the separate `andreaviselli.github.io` repository. This repository must not contain or publish that website.

## Option A: keep reviews local

Benefits:

- simplest security and support model;
- papers and reports stay on the user's machine except for provider processing;
- no central upload, login, or abuse risk;
- run directories are easy to inspect and move.

Costs:

- users need Python and a terminal;
- users manage their key, files, deletion, and provider costs;
- there is no browser progress screen.

This is the supported option today.

## Option B: website with a hosted backend

The website would send a paper or approved URL and non-secret settings to a separate HTTPS service. That service would create a background job, keep private files, run ETS4 with server-side keys, and expose protected status, resume, cancel, and download endpoints.

It would need:

- login and access checks for every run;
- file and storage limits;
- encrypted private storage;
- a background queue, retries, cancellation, and separate workers;
- server-side provider keys and per-user budgets;
- malware scanning, private-address blocking, rate limits, and abuse controls;
- clear retention and provider-processing rules;
- no public report links;
- audit records and service monitoring.

This would be easier for users but much harder to operate safely.

## Option C: bring a key in the browser

This is not recommended or implemented. A browser key and PDF can be exposed to page scripts, extensions, browser storage, developer tools, crash logs, and third-party dependencies. Long model calls and large uploads also fit poorly in a browser-only design.

Even an experimental version would need an expiring key, no default persistence, no key transfer to the website server, and explicit browser support from the provider. Those steps do not remove the privacy risk.

## Recommended order

1. Keep the packaged local CLI as the review interface.
2. Update the public information page so it describes the current three-stage process.
3. Build a separate background API only if users need browser-launched reviews.
4. Finish its security and privacy design before connecting the website.

Human scoring and a second provider are optional. They do not block a correct information page or local use.

## Possible API

```text
POST /v1/reviews
GET  /v1/reviews/{run_id}
POST /v1/reviews/{run_id}/resume
POST /v1/reviews/{run_id}/cancel
GET  /v1/reviews/{run_id}/artifacts
GET  /v1/providers
```

`POST /v1/reviews` would accept either a server-issued upload token or an approved manuscript URL, plus provider, model, and panel size. It would return `202 Accepted`, a run ID, and a status URL. It must never accept a provider key from browser code.

Status would show progress and whether the run can resume. The file list would return short-lived protected links with media type and checksum. Website code would use JSON over HTTPS and never import the ETS4 Python package.

`src/ets4/api/contracts.py` holds early data shapes only. Login, uploads, HTTP routes, and workers are not built.
