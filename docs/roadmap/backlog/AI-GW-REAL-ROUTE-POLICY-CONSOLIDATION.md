# AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION

Status: `PLANNED`
Owner role: Architecture and privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before opening and after any provider-route change

## Goal

Make the real Workspace Chat provider route use one verified AIOS policy boundary
for privacy labels, source-set consent, destination/purpose binding, payload
sanitization and safe provider request construction.

## Context

Current `real_router_enabled` behavior blocks `local_only`, `confidential` and
`unknown` labels, requires an explicit confirmation and rejects changed enabled
source sets. The router-enabled mock/preflight path uses `BrainGateway` for
stronger source-set/destination/purpose validation and sanitization. The real
route is not proven to invoke that Gateway contract before building a provider
prompt.

## Non-goals

- No new cloud-default behavior or provider.
- No bypass/relaxation of local-first or existing hard blocks.
- No RAG v2 hybrid retrieval, A18 or P1.0 scope.
- No storage migration or normal-user technical panel.

## Preconditions

- Professionalization baseline is completed with current evidence.
- Existing real-route privacy regression suite is green.
- Destination naming/consent semantics have an ADR-compatible decision.

## Intended scope

- Trace all Workspace Chat real-provider call paths.
- Adapt real route to consume `BrainDecision`/sanitized payload or an equivalent
  single policy interface with no weaker semantics.
- Preserve/extend localized safe errors and source-set change detection.
- Add tests proving blocked labels, missing/invalid consent, destination/purpose
  mismatch, path/secret sanitization and no provider call on denial.
- Update ADR-0004, runtime contracts, threat model and privacy assessment.

## Acceptance evidence

- Focused privacy/provider route tests demonstrate one enforcement contract.
- Provider client receives no raw local path/secret metadata in test fixtures.
- Full quality gates pass: docs check, compile, pytest, CLI audit and Workspace
  Chat import.
- No live credential or private source is needed for test evidence.

## Rollback

Retain a documented last-known-safe route implementation. Revert only the
consolidation slice if regression occurs; never disable hard privacy blocks as a
rollback shortcut.
