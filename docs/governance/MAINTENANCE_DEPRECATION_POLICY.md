# Maintenance and Deprecation Policy

Status: `PROPOSED`
Owner role: Project owner / maintainer
Last reviewed: 2026-07-25
Review cadence: Each release candidate and retirement decision

## Maintenance

Maintain supported Workspace Chat, privacy boundary, local data safety and
quality gates first. Planned features do not become support commitments merely
because design documents exist.

## Deprecation lifecycle

1. Record rationale, affected modules/data and replacement in an ADR/Gate Card.
2. Mark documentation/routes as deprecated while preserving historical evidence.
3. Remove supported launcher/import expectations only after compatibility review.
4. Keep shared services until dependency/capability audit approves removal.
5. Record validation, rollback and residual risk in roadmap/changelog/handover.

## Current examples

Studio and public Case Cockpit routes are retired. Shared Case Cockpit services
are not automatically deletable; their retirement remains separately planned.

## Support window

Release support duration and end-of-life dates are `OWNER_DECISION_REQUIRED`.
