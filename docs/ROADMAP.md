# ETS4 roadmap

## Working now: local review

- safe full-PDF input;
- three versioned prompt stages;
- checked shared data models;
- mock and OpenAI providers;
- separate referee calls, limited parallel work, retries, resume, and cancellation;
- Markdown and JSON reports;
- command-line interface;
- repeatable tests.

A local PDF or supported URL can complete all stages. If one referee fails, ETS4 keeps completed work and can resume without repeating it.

## Current priority: package release

Follow [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): finish metadata, choose a licence, test built files in a clean environment, and prepare a safe release process. Until then, users install the package from a repository checkout.

The separate `andreaviselli.github.io` site should also describe the current review tool instead of the old digest product. That page can be corrected without building a hosted review service.

## Optional improvements

Add these only when there is a clear need:

- use the human scoring guide for an important prompt or model change;
- add another provider for a specific portability or feature goal;
- maintain model context and PDF capability data;
- cancel in-progress provider requests when an SDK supports it;
- add OCR with visible source tracking;
- lock runs against two processes resuming them at once;
- define encrypted local or managed storage.

None of these blocks current local reviews.

## Possible hosted API

A hosted service would need background jobs, login, private storage, per-user access, quotas, malware scanning, network restrictions, deletion jobs, audit records, and abuse controls. Provider keys must stay on the server.

Build this only if website visitors need to launch reviews. A security and privacy review must pass before the public site connects to it.

## Out of scope

- automatic publication or journal decisions;
- browser-side provider keys as the normal design;
- general web searches about a paper or its authors;
- discussion between referees or shared sessions;
- adding referees after the fixed panel reports;
- using confidential papers for training or evaluation without permission.
