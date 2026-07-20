# CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT

Status: `PLANNED`

## Goal

Produce the exact dependency/capability matrix required to retire the Case
Cockpit monolith safely.

## Required evidence before deletion

- Every import of `case_*`, visual-map, strong-answer and handoff modules.
- Classification: current shared service, cockpit-only service, test-only or dead.
- Workspace Chat replacement/retirement decision for each user capability.
- Focused replacement tests plus full validation.
- Explicit rollback plan and owner approval for the source deletion slice.

No Case Cockpit source/service deletion is authorized by this card alone.
