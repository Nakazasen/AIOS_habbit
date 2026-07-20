# DOCS-LEGACY-CLEANUP-RESET

Status: `ACTIVE`

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

## Verification

- `git diff --check`
- Markdown link/path review for canonical docs
- full validation runs before gate closure

## Rollback

All changes are documentation/path changes. Restore named files or archive moves
from Git if a reference must be reinstated.
