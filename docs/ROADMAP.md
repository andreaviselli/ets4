# ETS4 roadmap

## Phase 1: reliable local core - implemented

- secure complete-manuscript ingestion
- three versioned prompt stages
- validated provider-neutral schemas
- mock and OpenAI adapters
- durable orchestration, isolation, concurrency, fan-in, resume, cancellation
- Markdown/JSON run artifacts
- terminal interface
- deterministic test suite

Exit condition: a local PDF or supported URL completes all three stages with the mock provider, and recoverable referee failure resumes without repeating completed calls.

## Current priority: documentation and public-page alignment

- record the two completed OpenAI reviews of real manuscripts in the project state;
- describe scanned/image-only and very long PDF limits accurately;
- update the ETS4 page in the separate `andreaviselli.github.io` repository;
- keep the local CLI as the supported review interface.

This work does not require a hosted service. The public page can explain the current process without accepting manuscript uploads or launching reviews.

## Optional future work: validation and operational hardening

- use the existing behavioral rubric when a future prompt or model change warrants formal comparison;
- add a second provider only if cross-provider portability becomes a concrete goal;
- maintain explicit capability and context-limit data
- add provider-specific cancellation where supported
- add optional reliable OCR with visible provenance
- add process-level run locking for concurrent resume/status operations
- define encrypted local or managed storage profiles

These are improvements, not blockers for current local reviews.

## Optional future work: hosted API

- implement authenticated asynchronous jobs behind `src/ets4/api/contracts.py`
- add private object storage, per-user authorization, quotas, malware scanning, egress controls, deletion jobs, audit events, and abuse prevention
- document and test the website-to-backend contract
- keep provider keys server-side

Exit condition: security/privacy review passes and the separate website can submit, poll, resume, and retrieve artifacts without importing ETS4 internals.

## Optional future work: interactive website integration

- update `andreaviselli.github.io`, not this repository
- connect through the versioned HTTPS API contract
- provide clear confidentiality, retention, cost, and experimental-review notices
- retain a human editorial decision outside automation

Exit condition: browser users can use the hosted service without exposing provider keys or conflating artificial recommendations with journal decisions.

## Explicitly out of scope

- autonomous publication or journal decisions
- browser-side provider keys as the default design
- general web search about a manuscript or its authors
- reviewer-to-reviewer discussion or shared sessions
- dynamically adding referees after the fixed panel has reported
- training or evaluating on confidential manuscripts without authorization
