# ADR-0001: Local-first Filesystem Ownership

Status: `ACCEPTED`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before storage, synchronization or external-processing changes

## Context

AIOS WorkLens stores work knowledge and may process sensitive owner documents.
The constitution requires local-first behavior and long-term portability.

## Decision drivers

Confidentiality, owner control, offline usefulness, auditability and avoidance of
AI/vendor lock-in outweigh centralized synchronization convenience.

## Options considered

1. Cloud-first managed workspace.
2. Local-first files with optional explicitly authorized external calls.
3. Router/provider-owned storage.

## Decision

Use local-first filesystem ownership. Workspace Chat state is stored in ignored
`local_cases/`; evidence/memory and other runtime artifacts are also excluded
from Git. Cloud routing, when used, is an explicit optional boundary.

## Consequences

- Backup, restore and device-transfer are owner operational responsibilities.
- Shared multi-device synchronization is not a current product guarantee.
- Documentation and exports must avoid embedding private data.

## Security and privacy impact

This reduces default external disclosure but does not replace disk encryption,
OS account security or a user-managed backup procedure.

## Migration and rollback

No data migration is required for this decision. Any future synchronized storage
requires a new ADR, privacy assessment, threat-model update and migration plan.

## Evidence

- [Constitution](../../CONSTITUTION.md)
- [Data policy](../../00_governance/DATA_POLICY.md)
- [Privacy impact assessment](../security/PRIVACY_IMPACT_ASSESSMENT.md)
