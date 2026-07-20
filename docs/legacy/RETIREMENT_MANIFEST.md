# Legacy Retirement Manifest

## Boundary

Workspace Chat là primary UI. Legacy source không được xem là supported user route.
Runtime data `local_cases/` và `local_runs/` không thuộc cleanup source và phải tiếp
tục Git ignored.

## Inventory

| Item | Classification | Action | Evidence / rollback |
|---|---|---|---|
| `studio.py` | `RETIRE` | Delete with Studio-only console route/docs/tests | No production import found; restore from Git if needed |
| `RUN_AIOS_HABIT_STUDIO.bat`, `scripts/run_studio.ps1` | `RETIRE` | Remove after Workspace Chat launcher is verified | Recreate from Git history only if required |
| `aios-habit-studio` | `RETIRE` | Remove package entry | `pyproject.toml` only route |
| `RUN_AIOS_CASE_COCKPIT.bat`, `scripts/run_case_cockpit.ps1` | `RETIRE` | Remove public direct routes | Case source stays pending next slice |
| `aios-case-cockpit` | `RETIRE` | Remove package entry | Case source stays pending next slice |
| `case_cockpit.py` | `MIGRATE_OR_DELETE` | Do not delete in this slice | ~3k-line UI and cockpit-only tests; shared services must be audited |
| `case_*`, visual map, handoff services | `AUDIT_REQUIRED` | Keep until dependency/capability matrix is approved | Several non-cockpit modules/tests still import them |
| `mom_*` pilot | `KEEP_ISOLATED` | Retain as benchmark/reference until RAG v2 evaluation replaces it | No RAG v2 core dependency |

## Completion criteria for the Studio/public-route slice

1. Only Workspace Chat launchers are documented and tested.
2. No public console script references Studio or Case Cockpit.
3. No active README/install/operator docs route users to legacy.
4. `studio.py` and Studio-only documentation/tests are removed.
5. Full compile/test/audit passes; runtime ignored files remain untouched.
