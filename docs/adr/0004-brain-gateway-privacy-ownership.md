# ADR-0004: Brain Gateway Owns Privacy and Consent Decisions

Status: `ACCEPTED`
Owner role: Project owner / privacy reviewer
Last reviewed: 2026-07-25
Review cadence: Before a data label, consent or external-route change

## Context

Provider routing must not decide whether owner data may leave the local process.
The product needs default-deny behavior, explicit consent for sensitive classes
and sanitized payloads.

## Decision

`BrainGateway.preflight_check()` owns the canonical privacy classification,
source-set hashing, consent validation, outbound-evidence authorization and
sanitization contract. Both the router-enabled mock path and the real Workspace
Chat provider path now create a `BrainRequest` and invoke this contract before
an adapter is eligible to run.

The real Workspace Chat route uses the stable destination
`workspace_chat_external_router` and purpose `workspace_chat_answer`. It
checks policy against the full enabled source snapshot even when local retrieval
selects only a subset. The real adapter accepts only `SanitizedRouterPayload`,
so provider messages cannot be supplied as independently built raw prompts.

## Consequences

- Provider adapters receive only a permitted/sanitized payload contract.
- `local_only`/`confidential` are hard-denied; `unknown`/`machine_only` require
  bound consent. The explicit owner sharing choice creates `cloud_safe`.
- Legacy stored `machine_only`/`cloud_allowed` labels remain non-sendable until
  the owner makes a new explicit sharing choice; there is no silent migration.
- Label selection remains an owner responsibility and residual risk.

## Security and privacy impact

This is the core control for data minimization at the external-provider boundary.
It must be tested on every material route change.

## Migration and rollback

Any label/consent semantic change requires a new ADR, privacy-assessment update,
regression tests and a compatibility statement for stored source labels.

## Evidence

- [Gateway source](../../src/aios_habit/brain_gateway.py)
- [Threat model](../security/THREAT_MODEL.md)
- [Privacy impact assessment](../security/PRIVACY_IMPACT_ASSESSMENT.md)
