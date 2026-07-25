# DOCS-LEGACY-CLEANUP-RESET

Status: `DONE`

## Goal

Replace contradictory current-facing documentation, create a single roadmap
source, and classify historical evidence without losing traceability.

## In scope

- `README.md`, `PROJECT_HANDOVER.md`, `WORKLENS_ARCHITECTURE.md`
- install/operator/developer runbooks
- canonical `ROADMAP.md`, retired master-roadmap redirect
- Gate Card convention, archive policy and retirement manifest
- archive legacy UX/design evidence without editing its historical claims

## Non-goals

- No RAG runtime feature work.
- No Case Cockpit monolith/service deletion.
- No runtime/private data migration.

## Acceptance criteria

1. Normal user docs name Workspace Chat as the only supported UI.
2. One canonical roadmap identifies active/planned/retired status.
3. Gate Cards distinguish active work from historical audit evidence.
4. Staged documentation with stale claims is preserved as archive, not committed
   as current architecture/roadmap truth.

## Verification evidence

Verified on 2026-07-25:

- Implementation commit: `9123caa` (`Clean legacy routes and reset project documentation`).
- Compile: passed.
- Full pytest: `892 passed`.
- CLI audit: passed.
- The intentional secret-pattern fixtures are constructed at runtime, preserving
  detector coverage without storing complete fake credential literals in source.
- `git diff --check`: passed before closure.

## Rollback

All changes are documentation/path changes. Restore named files or archive moves
from Git if a reference must be reinstated.
