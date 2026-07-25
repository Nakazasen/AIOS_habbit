# ADR-0002: Workspace Chat Is the Supported User Interface

Status: `ACCEPTED`
Owner role: Project owner / product and architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before adding or retiring a public user route

## Context

Legacy Studio and Case Cockpit public routes created contradictory normal-user
entry points. Current product direction requires a simple source-select → ask →
check-citation flow.

## Options considered

1. Keep multiple public UIs.
2. Make Workspace Chat the only supported user UI while keeping shared legacy
   services until separately audited.
3. Remove all legacy services immediately.

## Decision

Workspace Chat is the only supported normal-user route. Public legacy launchers
and routes are retired; shared legacy services remain outside this decision until
their dependency/capability audit authorizes removal.

## Consequences

- User docs and release checks point to Workspace Chat only.
- Legacy modules cannot be reintroduced into supported UI imports.
- Service deletion remains a separately controlled backlog item.

## Security and privacy impact

A single supported entry point makes privacy messaging, error handling and
operator guidance easier to audit. It does not authorize cloud routing.

## Migration and rollback

Rollback restores a specific retired launcher/module from Git after a route
review; it does not restore obsolete documentation as current truth.

## Evidence

- [Canonical roadmap](../../ROADMAP.md)
- [Retirement manifest](../legacy/RETIREMENT_MANIFEST.md)
- [Runtime interfaces](../contracts/RUNTIME_INTERFACES.md)
