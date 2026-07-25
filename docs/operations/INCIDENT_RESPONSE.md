# Incident Response

Status: `PROPOSED`
Owner role: Project owner / designated incident coordinator
Last reviewed: 2026-07-25
Review cadence: After incident, release candidate or security boundary change

## Purpose

Contain, investigate and recover from a suspected privacy, credential, integrity
or availability incident without spreading additional private data.

## Severity model

| Level | Example | Immediate objective |
|---|---|---|
| SEV-1 | Suspected exposed credential/private data in public location | Stop disclosure, revoke/contain, preserve minimal evidence |
| SEV-2 | Local data loss/corruption or provider route may violate policy | Stop affected flow, restore/assess scope |
| SEV-3 | Provider outage, failed release or non-sensitive functional regression | Restore supported local behavior |
| SEV-4 | Documentation/process gap without active impact | Track in risk register and plan correction |

## First response

1. Do not paste a secret, raw document, full prompt, local path or screenshot into
   a public issue/chat.
2. Stop the affected route/process where safe. For a provider concern, disable
   the router path and use local-only workflow.
3. Preserve minimal safe facts: time, version/commit, affected feature, observed
   status and whether data/credential exposure is suspected.
4. If a credential may be exposed, revoke/rotate it through the provider or owner
   secret process. Do not test the old key repeatedly.
5. If a private file was staged, remove it from the index without deleting owner
   data; escalate any pushed/remote exposure to SEV-1.

## Investigation and containment

- Reproduce only with synthetic data where possible.
- Review `git status`, audit output and sanitized logs; never create a raw-data
  diagnostic artifact in the repository.
- Determine whether gateway default-deny/consent/sanitization was involved for
  external-route concerns.
- Prefer rollback to last validated dependency/release over unreviewed hot edits.

## Recovery and communication

- Follow [backup and restore](BACKUP_RESTORE.md) for local data recovery.
- Follow [troubleshooting](TROUBLESHOOTING.md) for safe failure isolation.
- Security reporting channel, owner names, notification recipients and disclosure
  timeframes are `OWNER_DECISION_REQUIRED`; see root `SECURITY.md`.
- Record a sanitized post-incident note: timeline, impact class, root cause,
  corrective action, verification and residual risk. Link it from the risk
  register without private evidence.

## Closure criteria

An incident closes only after containment, recovery/rollback evidence, regression
validation, owner communication decision and risk/ADR/runbook updates are
recorded. No incident is closed solely because an error disappeared.
