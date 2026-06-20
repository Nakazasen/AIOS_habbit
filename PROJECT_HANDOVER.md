# Project Handover

AIOS_habbit is now the central product repo for AIOS WorkLens / AIOS Case Cockpit.

## Current State
- CLI platform: PASS.
- AIOS Habit Studio: implemented.
- AIOS Case Cockpit v0.1: implemented.
- WorkLens governance docs: added.
- 4-repo inheritance audit: completed read-only with no source code copied.

## Product Loop
Case → Evidence → Map → Action → Learning.

## Validation
- Full compileall: PASS.
- Full pytest: PASS.
- CLI audit: PASS.
- Case Cockpit import: PASS.
- Streamlit import: PASS.

## Public Safety
Runtime/local private data is ignored and must not be committed: `local_cases/`, evidence JSONL, memory JSONL, export packs, raw office docs, screenshots, `.env`, tokens, secrets, credentials, caches.

## Next Steps
1. Run Monday pilot using `RUN_AIOS_CASE_COCKPIT.bat`.
2. Capture sanitized feedback only.
3. Do not port code from inheritance repos until a feature has source, reason, tests, owner module, and rollback path.
4. Use `docs/inheritance_audit/INHERITANCE_SUMMARY.md` to prioritize harvest candidates.
