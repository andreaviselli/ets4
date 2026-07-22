# Data and privacy

## Local files

A run directory contains the complete manuscript, extracted page text, all reports, model details, usage, and possibly raw model responses. Treat the whole directory as confidential.

Raw responses are kept by default for local auditing. Disable this with:

```bash
ets4 review manuscript.pdf --no-retain-raw-responses
```

This setting does not remove the checked reports or change provider-side processing. Delete run directories according to the manuscript owner's rules. ETS4 has no automatic deletion command.

## OpenAI processing

The adapter sends the PDF inline to the Responses API and sets `store=false` by default. It does not create a Files API object. Current OpenAI documentation says API data is not used for training by default, but safety monitoring and file scanning may still keep some data. Zero Data Retention and Modified Abuse Monitoring are separate controls for eligible organizations. Provider rules can change, so check them before handling confidential work.

Reference: [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

`store=false` does not promise zero retention. Do not submit confidential, personal, export-controlled, or regulated material unless you have permission and the provider terms allow it.

## What hosting would require

A hosted ETS4 service must define, build, and publish:

- the legal basis and user permission for processing manuscripts;
- login and per-user access rules;
- encrypted connections and storage;
- separation between users;
- provider and region details;
- retention periods for raw and checked files;
- deletion and export tools;
- backup and log lifetimes;
- staff access and audit records;
- incident response;
- cost and abuse controls.

Do not copy the local defaults into a hosted service without this work.

## Logs and manifests

Normal event logs contain stage names, state changes, times, and safe provider error details. Errors may include a short message, code, rejected parameter, HTTP status, request ID, provider, and exception type. They do not include prompts, manuscript text, reports, API keys, headers, full requests, or hidden reasoning. Raw responses stay only under `logs/raw/` when enabled.

The manifest records the submitted source. For a local file, that source can be an absolute path on the machine. Run directories are ignored by Git and must not be committed or published.
