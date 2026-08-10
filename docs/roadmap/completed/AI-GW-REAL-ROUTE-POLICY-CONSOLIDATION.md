# AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION

Status: `DONE`
Owner role: Architecture and privacy reviewer
Last reviewed: 2026-07-25
Review cadence: After any provider-route change

## Goal

Make the real Workspace Chat provider route use one verified AIOS policy boundary
for privacy labels, source-set consent, destination/purpose binding, payload
sanitization and safe provider request construction.

## Context

`real_router_enabled` now builds a `BrainRequest` from the full enabled source
snapshot and calls `BrainGateway.preflight_check()` before it invokes the router.
The gateway binds consent to `workspace_chat_external_router` and
`workspace_chat_answer`, authorizes the retrieval subset against the full
snapshot, and returns the only payload accepted by the real router adapter.

## Non-goals

- No new cloud-default behavior or provider.
- No bypass/relaxation of local-first or existing hard blocks.
- No RAG v2 hybrid retrieval, A18 or P1.0 scope.
- No storage migration or normal-user technical panel.

## Preconditions

- Professionalization baseline is completed with current evidence.
- Owner approved the external destination and conservative label handling.
- Existing real-route privacy regression suite is green.

## Allowlist

- `src/aios_habit/brain_gateway.py`
- `src/aios_habit/workspace_chat_ai_answer.py`
- `src/aios_habit/workspace_chat_router_adapter.py`
- `src/aios_habit/workspace_chat_retrieval.py`
- `src/aios_habit/workspace_chat_ui.py`
- Gateway, Workspace Chat answer and owner-flow regression tests.
- The documentation records explicitly linked below.

## Implemented scope

- Real route uses the canonical Gateway before external prompt creation.
- Consent is bound to the exact full source snapshot, destination and purpose.
- `local_only` and `confidential` remain hard-denied; `unknown` and
  `machine_only` remain default-denied without valid consent.
- Explicit “send externally” owner choice creates `cloud_safe`; legacy
  `machine_only` and `cloud_allowed` labels remain non-sendable by default.
- The real adapter accepts `SanitizedRouterPayload` only and builds its provider
  messages internally; it cannot accept independently built raw prompts.
- Retrieved evidence retains its parent source identity so outbound snippets are
  authorized against the full enabled source set.

## Acceptance and closure evidence

Verified on 2026-07-25:

- Focused compile and privacy/provider-route regression suite: `155 passed`.
- Documentation contract: `PASS`; full compile: `PASS`; full pytest:
  `903 passed in 18.16s`.
- CLI audit: `PASS` with no errors or warnings; Workspace Chat import: `PASS`
  (expected Streamlit bare-mode warnings only).
- `git diff --check` and `git diff --cached --check`: `PASS`.
- Tests prove hard-deny/no adapter call, missing consent deny, stale source-set
  deny, full-snapshot enforcement for retrieved evidence, typed sanitized adapter
  input, raw-prompt rejection, and path/key redaction before routing.
- CI evidence uses synthetic fixtures only; no provider credential or live call.

## Closure status

The implementation and required validation are complete. This gate may support
external-provider release evidence only within the separate release-policy and
owner-decision constraints.


## Rollback

Revert only this consolidation slice if regression occurs; never disable hard
privacy blocks or reintroduce raw-prompt adapter inputs as a rollback shortcut.

