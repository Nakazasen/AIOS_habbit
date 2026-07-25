# Contributing to AIOS WorkLens

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-07-25
Review cadence: Each release candidate and contributor workflow change

## Before changing code or documentation

1. Read `CONSTITUTION.md`, `ROADMAP.md`, `PROJECT_HANDOVER.md` and the relevant
   Gate Card.
2. Read the linked ADR, requirement, contract, threat/privacy and test records.
3. Keep changes inside the gate allowlist. Do not start a planned feature without
   an active scope decision.

## Privacy and data rules

Never commit or paste into issues/PRs: API keys, `.env` values, `local_cases/`,
`local_runs/`, raw documents, screenshots, private JSONL/SQLite data, full prompts
or provider Authorization data. Use synthetic fixtures and sanitized logs.

## Change workflow

- Keep a change small and traceable to requirement/ADR/test evidence.
- Add focused tests for changed behavior.
- Update canonical docs when behavior, route, contract or risk changes.
- Preserve Vietnamese-first user copy and safe error behavior.
- Do not bypass audit or delete failing tests to obtain a pass.

## Required validation

Run [quality gates](docs/quality/QUALITY_GATES.md) before review. A maintainer
must inspect the diff and Git status for private/runtime artifacts.

## Review expectations

Reviewers check scope, architecture, privacy/security, tests, operational impact,
rollback and documentation evidence. New provider routes, persistent-data changes,
dependencies and public UI routes require the roles listed in
[ownership and review](docs/governance/OWNERSHIP_AND_REVIEW.md).
