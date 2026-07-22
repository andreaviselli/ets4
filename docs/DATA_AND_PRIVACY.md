# Data and privacy

## Local data

A run directory contains the complete manuscript, extracted page text, all structured and rendered reports, model identifiers, usage, and possibly raw responses. Treat the entire directory as confidential.

Raw retention defaults to enabled for local audit. Disable it with:

```bash
ets4 review manuscript.pdf --no-retain-raw-responses
```

Disabling raw retention does not remove the validated report artifacts or provider-side processing. Delete local run directories according to the manuscript owner's policy; ETS4 has no automatic local deletion command in this foundation.

## OpenAI processing

The adapter uses inline base64 Responses API file input and `store=false` by default. It does not create a Files API object. According to current official documentation, API data is not used for training by default, but abuse-monitoring retention and file-input safety scanning can still apply; Zero Data Retention and Modified Abuse Monitoring require eligible organizational controls. Provider policies may change, so verify them before confidential use.

Reference: [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

Do not interpret `store=false` as a promise of zero retention. Do not submit confidential, personal, export-controlled, or regulated material unless authorization and provider terms permit it.

## Hosted profile requirements

A hosted ETS4 backend must define, implement, and publish:

- lawful basis and user authorization for manuscript processing;
- per-user authentication and authorization;
- encrypted transport and storage;
- tenant isolation;
- provider and region disclosures;
- raw/validated artifact retention durations;
- user deletion/export procedures;
- backup and log lifecycle;
- staff-access controls and audit trails;
- incident response;
- cost and abuse controls.

Local defaults must not be copied blindly to hosted execution.

## Logs and manifests

Normal event logs contain state changes, stage names, timestamps, and sanitized provider failures. Provider failures are limited to message, error code, rejected parameter, HTTP status, request ID, provider, and exception type. They do not contain prompts, manuscript prose, reports, API keys, headers, full request payloads, or hidden reasoning. Raw provider responses live only in the explicitly named `logs/raw/` area.

The manifest records the supplied source. For local files this can be an absolute runtime path; runtime directories are ignored and must not be committed or published.
