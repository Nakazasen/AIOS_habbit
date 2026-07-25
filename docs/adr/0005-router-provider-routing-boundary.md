# ADR-0005: Router Is a Provider-routing Dependency, Not a Policy Authority

Status: `ACCEPTED`
Owner role: Project owner / integration reviewer
Last reviewed: 2026-07-25
Review cadence: Each router upgrade or new provider integration

## Context

AIOS uses Nakazasen AI Router to select/call configured providers. Privacy,
product consent and source ownership are AIOS responsibilities.

## Decision

Pin and integrate the router as a provider-routing dependency. AIOS continues to
own policy decisions, prompt/source minimization, consent and user-facing error
handling. The direct Workspace Chat adapter consumes router outcomes and returns
safe Vietnamese messages; it never loads a key file as persistent application
configuration.

## Consequences

- Router upgrades need compatibility, focused tests and full validation.
- Router capabilities do not automatically authorize data egress.
- Live tests remain explicit, generic and use temporary environment injection.

## Security and privacy impact

The router is outside the policy authority. Provider terms, availability and
retention remain external-owner review obligations.

## Migration and rollback

Revert to the last validated router tag, reinstall in a clean environment and
rerun quality gates. Do not invoke automatic self-update on behalf of the owner.

## Evidence

- [Router adapter](../../src/aios_habit/workspace_chat_router_adapter.py)
- [Dependency policy](../security/DEPENDENCY_POLICY.md)
- [Release policy](../release/RELEASE_POLICY.md)
