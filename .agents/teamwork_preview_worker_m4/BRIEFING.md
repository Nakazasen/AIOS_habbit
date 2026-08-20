# BRIEFING — 2026-08-19T23:55:00Z

## Mission
Create a comprehensive acceptance test suite in `tests/test_mom_upgrade_acceptance.py` and verify 100% test pass rate across the full test suite.

## 🔒 My Identity
- Archetype: test writer
- Roles: specialist, qa
- Working directory: d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_worker_m4
- Original parent: 35b372f7-11c5-4120-b88a-3f8881102381
- Milestone: Milestone 4 (Acceptance & Full Regression Verification)

## 🔒 Key Constraints
- Write and modify test code only (`tests/test_mom_upgrade_acceptance.py`).
- Never edit implementation code; escalate defects if found.
- Do not cheat, fake, or facade tests.
- Ensure all tests are progressive, independent, and verifiable.
- Test R1, R2, R3, R4 thoroughly.

## Current Parent
- Conversation ID: 35b372f7-11c5-4120-b88a-3f8881102381
- Updated: 2026-08-19T23:55:00Z

## Task Summary
- **What to build**: Comprehensive acceptance test suite `tests/test_mom_upgrade_acceptance.py` testing:
  1. R1: MOM local index source inspection (0 hardcoded query terms/boosts/penalties) & BM25 ranking (CJK Japanese/Chinese, length normalization, non-negative scores).
  2. R2: Excel extraction (>1500 rows synthetic spreadsheet, full row extraction without truncation, header repetition, chunk metadata, config defaults).
  3. R3: Dynamic abstention verification (0 POLISHED_ANSWERS / static score/latency dicts, no canned refusals in benchmark runner, synthesize_evidence dynamic abstention).
  4. R4: Full pytest test suite 100% pass verification.
- **Success criteria**: All acceptance tests passing, 0 test failures across repo.
- **Interface contracts**: `PROJECT.md` § Interface Contracts
- **Code layout**: `PROJECT.md` § Code Layout

## Loaded Skills
- None explicitly loaded.

## Quality Status
- **Build/test result**: Running full test suite.
- **Lint status**: Clean.
- **Tests added/modified**: `tests/test_mom_upgrade_acceptance.py` (in progress).

## Key Decisions Made
- Write detailed unit and integration tests covering static code properties and dynamic execution properties for R1, R2, R3, and R4.

## Artifact Index
- `tests/test_mom_upgrade_acceptance.py` — Acceptance test suite
- `handoff.md` — 5-component handoff report
- `progress.md` — Liveness & progress tracker
