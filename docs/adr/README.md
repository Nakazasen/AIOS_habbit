# Architecture Decision Records

Status: `ACTIVE`
Owner role: Project owner / architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before a material architecture or boundary change

## Purpose

Architecture Decision Records (ADRs) preserve the context, alternatives and
consequences of material technical decisions. They are distinct from the
user-decision-pattern template in `11_templates/decision_record.md`.

## Lifecycle

- `ACCEPTED`: current decision.
- `SUPERSEDED`: replaced by a newer ADR that is linked.
- `DEPRECATED`: retained as history but no longer a recommended decision.
- `PROPOSED`: needs owner approval before implementation.

New ADRs receive the next zero-padded number and include context, decision
drivers, options, decision, consequences, security/privacy impact, rollback and
evidence links. Historical ADRs record known facts only; they do not claim that
unimplemented controls already exist.

## Index

1. [ADR-0001: Local-first filesystem ownership](0001-local-first-filesystem-ownership.md)
2. [ADR-0002: Workspace Chat as supported UI](0002-workspace-chat-supported-ui.md)
3. [ADR-0003: Local SQLite lexical index](0003-local-sqlite-lexical-index.md)
4. [ADR-0004: Brain Gateway owns privacy decisions](0004-brain-gateway-privacy-ownership.md)
5. [ADR-0005: Router is a provider-routing dependency](0005-router-provider-routing-boundary.md)
6. [ADR-0006: Private runtime data stays outside Git](0006-private-runtime-data-outside-git.md)
