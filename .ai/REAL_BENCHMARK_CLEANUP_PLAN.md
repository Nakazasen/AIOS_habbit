# Real Benchmark Cleanup Plan

## Generated runtime outputs
- `local_runs/` — ignored runtime benchmark outputs. Delete only generated files, never commit.
- `.pytest_cache/`, `__pycache__/`, `*.egg-info/` — ignored caches. Safe to delete if needed.
- `07_ai_export_packs/*/*_export_pack.md` — generated prompt/export packs. Keep ignored, do not commit.
- `08_audit/final_audit_report.md`, `09_handover/final_handover.md` — generated reports. Keep ignored, do not commit.

## Fake/demo/pilot/benchmark artifacts
- Unit tests use inline/temp fixtures and must be kept.
- `local_cases/` is ignored local runtime data. Do not commit.

## Source-controlled test fixtures
- `tests/` and `examples/` are kept unless a test explicitly replaces a fixture with temporary data.

## Real source docs
- `[LOCAL_SOURCE_ROOT]` is read-only for this benchmark. Do not delete, move, or commit its contents.

## Cleanup action
- Deleted: none in this pass.
- Kept: all test fixtures and real source docs.
- Replaced by temporary fixtures: new tests use `tmp_path` only.
- Risk: LOW. No destructive cleanup performed.
