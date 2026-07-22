# Website integration assessment

The public page belongs to the separate `andreaviselli.github.io` repository. This repository must not contain or publish that website.

## Option A: local-only execution

Advantages:

- simplest security and operating model;
- manuscripts and artifacts stay on the user's machine except provider processing;
- no central upload/authentication/abuse surface;
- run directories are directly auditable and reproducible.

Costs:

- Python installation and terminal use;
- users manage provider keys, local permissions, deletion, and costs;
- no browser progress interface.

This is the recommended current deployment.

## Option B: website plus hosted ETS4 backend

The website uploads a manuscript or submits a permitted URL and non-secret settings to a separate authenticated HTTPS API. The backend creates an asynchronous job, stores private artifacts, runs ETS4 workers with server-side provider keys, and exposes authorized status/resume/artifact endpoints.

Required controls:

- authenticated users and per-run authorization;
- upload and total-storage limits;
- private encrypted object storage;
- asynchronous queue, retries, cancellation, and worker isolation;
- server-side provider credentials and per-user cost quotas;
- malware scanning, SSRF-resistant egress, rate limits, and abuse prevention;
- documented retention/deletion and provider-processing policy;
- no public artifact URLs;
- audit events and operational monitoring.

Advantages are accessibility and centralized maintenance. Costs are substantial hosting, security, privacy, abuse, and support responsibility.

## Option C: browser bring-your-own-key

This is not recommended or implemented. It depends on provider-supported browser origins and CORS, exposes a high-value key and confidential PDF to page scripts, extensions, browser memory/storage, developer tools, crash logs, and supply-chain dependencies, and complicates large uploads and long-running calls.

If investigated experimentally, the key must be ephemeral, never persisted by default, never sent to the website server, and used only when the provider explicitly supports the browser model. Those measures do not remove manuscript confidentiality or extension/script risk.

## Recommended staged plan

1. keep the reliable local CLI as the current review interface;
2. update the informational ETS4 page in `andreaviselli.github.io` now so it describes the targeted review process rather than the archived digest;
3. build a separate asynchronous API only if website visitors should be able to launch reviews;
4. if that interactive service is pursued, complete its security and privacy design before connecting the website through the versioned API contract.

Formal human scoring and a second provider are optional future work, not prerequisites for correcting the public page or continuing local reviews.

## Proposed API contract

Future endpoints:

```text
POST /v1/reviews
GET  /v1/reviews/{run_id}
POST /v1/reviews/{run_id}/resume
POST /v1/reviews/{run_id}/cancel
GET  /v1/reviews/{run_id}/artifacts
GET  /v1/providers
```

`POST /v1/reviews` accepts one server-issued upload token or one permitted manuscript URL, provider/model selection, and referee count. It returns `202 Accepted`, `run_id`, and a status URL. It never accepts a provider API key from the browser contract.

Status returns workflow state, completed/failed stages, and resumability. Artifact listing returns short-lived authorized download URLs plus media type and checksum. Website code consumes JSON over HTTPS and does not import the ETS4 Python package.

Schemas are represented in `src/ets4/api/contracts.py`. Authentication, upload tokens, HTTP implementation, and worker queue are intentionally deferred rather than presented as functional.
