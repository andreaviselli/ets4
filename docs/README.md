# ETS4 documentation

The README is the quickest way to install and run ETS4. Use this page to find the deeper project notes without reading them in an arbitrary order.

## Start here

- [`REVIEW_PROTOCOL.md`](REVIEW_PROTOCOL.md): the three review stages and their hard boundaries.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): package layout, workflow order, and saved run state.
- [`DATA_AND_PRIVACY.md`](DATA_AND_PRIVACY.md): what leaves the machine and what stays in a run directory.
- [`SECURITY.md`](SECURITY.md): unsafe inputs, URL checks, secrets, and hosted-service requirements.

## Running and extending ETS4

- [`DEPLOYMENT.md`](DEPLOYMENT.md): supported local setup and what a hosted service would need.
- [`PROVIDERS.md`](PROVIDERS.md): provider rules and how to add another adapter.
- [`PROMPTS.md`](PROMPTS.md): prompt locations, versions, and change rules.
- [`TESTING.md`](TESTING.md): local checks, live tests, and human review of output quality.
- [`EVALUATION.md`](EVALUATION.md): the human scoring method.
- [`WEB_INTEGRATION.md`](WEB_INTEGRATION.md): options for the separate public website.

## Project records

- [`ETS4_STATE.md`](ETS4_STATE.md): what works now, recent checks, and known limits.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): the package and release plan.
- [`ROADMAP.md`](ROADMAP.md): optional product work after packaging.
- [`ETS4_DECISION_LOG.md`](ETS4_DECISION_LOG.md): important decisions and when to revisit them.
- [`adr/`](adr/): short records for the largest design choices.
- [`specification/SOURCE_DOCUMENTS.md`](specification/SOURCE_DOCUMENTS.md): hashes and priority order for the source PDFs.

Generated HTML, local run output, manuscripts, and raw provider responses do not belong in `docs/` or Git.
