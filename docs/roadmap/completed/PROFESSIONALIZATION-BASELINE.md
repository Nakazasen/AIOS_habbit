# PROFESSIONALIZATION-BASELINE

Status: `DONE`
Owner role: Project owner with security and release reviewers
Opened: 2026-07-25
Completed: 2026-07-25
Last reviewed: 2026-07-25
Review cadence: At each delivery slice and before gate closure

## Goal

Establish a maintainable, evidence-based professional documentation baseline for
AIOS WorkLens without changing its product runtime, UI flow, data schema or
local-first default.

## In scope

- Security, privacy, threat-model and dependency-governance records.
- Architecture implementation views, ADRs, requirements and traceability.
- Quality strategy, documentation contract checks and CI parity.
- Recovery, incident, troubleshooting, observability and release procedures.
- Risk, ownership, contributor, accessibility, migration, maintenance and
  onboarding records.
- Canonical documentation index and links from root project documents.

## Non-goals

- No RAG v2 hybrid retrieval implementation.
- No A18 or P1.0 opening.
- No new normal-user UI or technical panel.
- No cloud-default behavior, telemetry, secret storage or private-data migration.
- No invented SLA, legal compliance, retention duration, named owner or security
  disclosure contact.

## Preconditions

- Preserve the existing local-first and privacy-first constitution.
- Preserve uncommitted router v0.4.0 and cleanup-gate changes.
- Treat all runtime/private data as Git-ignored.

## Allowlist

- Documentation under `docs/`, root governance docs, contributor/security files.
- Documentation validation script/tests and CI configuration.
- No runtime application code except a documentation-only validation utility.

## Privacy constraints

- Never include API keys, local document text, screenshots, local paths or
  runtime JSONL/SQLite data in documentation, fixtures, CI artifacts or reports.
- Network/live-provider checks remain manual and opt-in; CI is offline by
  default.
- Any control not proven in source/tests is labelled `PLANNED`, `PARTIAL` or
  `OWNER_DECISION_REQUIRED`.

## Acceptance criteria

1. Required professional documents have owner role, status, review date/cadence
   and working local links.
2. Threat, privacy, release and operations docs reflect verified code behavior.
3. ADRs, requirements and traceability connect critical decisions to source,
   tests and runbooks.
4. Documentation contract check is automated and covered by tests.
5. CI executes compile, test, audit, Workspace Chat import and docs check.
6. Full repository validation passes with no private data tracked.

## Closure evidence

- Professional documents, metadata and local links: `DOCUMENTATION_CONTRACT=PASS`.
- Documentation/SBOM tooling tests: `4 passed`.
- Full repository suite: `896 passed in 30.64s`.
- Compile: PASS; CLI audit: `PASS` with no errors/warnings; Workspace Chat import:
  PASS (Streamlit bare-mode warnings only).
- Synthetic backup/restore drill: PASS for six Workspace Chat JSONL entity types
  plus SQLite index `count()`/lexical `search()`, using a temporary directory only.
- `git diff --check` and `git diff --cached --check`: PASS.
- `API Key.txt` and generated `local_runs/sbom/aios-habit-sbom.json`: confirmed
  ignored/untracked.

## Residual decisions and follow-up

Security reporting contact, distribution/support, retention/RTO/RPO, named
reviewers/CODEOWNERS handles and dependency advisory enforcement remain
`OWNER_DECISION_REQUIRED`. The completed
[AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
gate delivered the separate runtime control-flow change and its required
route-specific verification before the stronger external-provider release claim
can be considered.

## Verification

```powershell
py -3 scripts/check_docs.py
py -3 -m compileall src tests
py -3 -m pytest -q
$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit
$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

## Rollback

Revert the professionalization documentation, CI and documentation-check changes.
No runtime data migration, provider call, secret change or UI behavior requires
rollback in this gate.
