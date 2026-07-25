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

`BrainGateway.preflight_check()` owns the canonical target contract for privacy
classification enforcement, source-set hashing, consent validation and
sanitization. Its router-enabled preflight/mock path hard-denies
`local_only`/`confidential`, defaults unknown sources to deny, and requires valid
consent for `unknown`/`machine_only` data before an external route is eligible.

The current real Workspace Chat provider path has separate controls for allowed
labels, confirmation and source-set snapshot, but is not proven to invoke the
Gateway sanitizer/preflight. It is therefore a `PARTIAL` realization of this ADR;
[AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](../roadmap/backlog/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
must unify/verify enforcement before an external-release claim.

## Consequences

- Provider adapters should receive only a permitted/sanitized payload contract.
- Existing real route divergence is a P0 security/architecture follow-up, not a
  license to bypass the canonical policy boundary.
- Label selection is still an owner responsibility and is tracked as residual
  risk.

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
