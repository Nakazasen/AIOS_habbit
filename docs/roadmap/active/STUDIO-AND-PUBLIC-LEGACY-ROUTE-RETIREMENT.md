# STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT

Status: `ACTIVE`

## Goal

Remove public executable paths to legacy Studio/Case Cockpit and make Workspace
Chat launcher naming truthful.

## Scope

- Add `RUN_AIOS_WORKSPACE_CHAT.bat` and `scripts/run_workspace_chat.ps1`.
- Remove package console routes for Studio and Case Cockpit.
- Remove Studio source and Studio-only documentation/tests.
- Remove direct Case Cockpit launch scripts and their route-only assertions.
- Keep Case Cockpit source/shared services for the next audited retirement slice.

## Non-goals

- Do not delete `case_cockpit.py` in this gate.
- Do not delete any `case_*`, map, handoff, router or MOM service only because it
  was used by a legacy UI.

## Acceptance criteria

1. README/install/operator docs point only to Workspace Chat launchers.
2. Package scripts expose no Studio/Cockpit command.
3. No Studio module, old Studio launcher or direct Case Cockpit launcher remains.
4. Workspace Chat boundary regression succeeds.
5. Full test, compile and CLI audit pass; ignored runtime assets stay untouched.

## Rollback

Git can restore a removed launcher/module. No local runtime data is changed.
