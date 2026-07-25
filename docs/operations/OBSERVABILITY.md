# Observability and Diagnostics

Status: `PROPOSED`
Owner role: Project owner / operations reviewer
Last reviewed: 2026-07-25
Review cadence: Before logging, telemetry or support-bundle changes

## Principle

AIOS WorkLens uses privacy-safe local diagnostics. It does not currently claim a
central telemetry, metrics backend or externally hosted monitoring service.

## Diagnostic categories

| Category | Allowed examples | Prohibited examples |
|---|---|---|
| Environment | Python/package versions, OS family, command exit code | API keys, environment values, home/user path |
| App state | Selected feature, safe reason code, count/status | Raw source text, notebook/message content |
| Router | Normalized status/error class, provider/model only when owner approves | Authorization header, key, full prompt/payload |
| Storage | Store category, file existence, index count | JSONL rows, SQLite raw data, owner document names |
| Git/quality | Audit/test result, tracked/ignored status | Private filenames/content from ignored paths |

## Logging rules

- Use localized safe user messages for supported UI errors.
- Keep internal exception text out of user UI unless sanitized.
- Do not add telemetry, crash upload or analytics without a new ADR, privacy
  assessment and owner approval.
- Diagnostic retention is `OWNER_DECISION_REQUIRED`; diagnostics remain local by
  default and must not be committed.

## Safe diagnostic bundle

A support bundle, if an owner explicitly requests one, contains only version
metadata, command statuses, normalized reason codes and redacted snippets. Build
it outside the repository, inspect it manually, and remove paths/secrets before
sharing. It must never include `local_cases/`, `local_runs/`, `.env`, API key
files, raw prompt content or SQLite/JSONL runtime stores.

## Health indicators

Current local readiness indicators are: docs contract PASS, compile PASS, tests
PASS, CLI audit PASS and Workspace Chat import PASS. Provider availability is not
a readiness requirement because provider use is optional.
