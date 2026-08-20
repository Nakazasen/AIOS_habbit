# Orchestration Plan — MOM System Upgrade

## Overview
This plan governs the complete end-to-end upgrade of the MOM (Meeting of Minutes / Operations) system in AIOS_habbit per `ORIGINAL_REQUEST.md`.

## Phased Strategy

### Phase 0: Survey & Discovery (Parallel Exploration)
- **Explorer 1 (Search & Retrieval Focus)**: Investigate `src/aios_habit/mom_local_index.py`, existing BM25/TF-IDF / RAG v2 integration, keyword scoring heuristics, HTML file penalties, and test coverage in `tests/`.
- **Explorer 2 (Excel Extraction Focus)**: Investigate `src/aios_habit/excel_extractors.py`, current 1,000-row and 20,000-cell limits, memory impact, chunking interface requirements, and existing excel test cases.
- **Explorer 3 (Abstention & Reporting Focus)**: Investigate `scripts/generate_ai_grounded_report.py`, `scripts/run_workspace_chat_12_questions.py`, `ClaimGuard` integration, `POLISHED_ANSWERS` dictionary usages, and failure modes on unanswerable questions.

### Phase 0.5: Synthesis & Architecture Blueprint
- Create `PROJECT.md` with Feature Inventory, Architecture Boundaries, Interface Contracts, and Milestones.
- Create `TEST_INFRA.md` for E2E and unit test specifications.

### Phase 1: Milestone Execution (Iterative Cycles)
For each milestone (M1, M2, M3, M4):
1. **Worker**: Implements solution cleanly, runs builds and pytest.
2. **Reviewers (2 parallel)**: Verify code quality, boundary handling, interface consistency.
3. **Challengers (2 parallel)**: Stress test edge cases and empirical correctness.
4. **Forensic Auditor**: Integrity verification (no shortcuts, no mock evasions, no hardcodes).
5. **Gate Check**: If PASS, advance milestone and update AgentMemory checkpoint.

### Phase 2: Final Verification & Acceptance
- Full pytest test suite run (pass 100%, zero warnings/errors).
- Clean Audit verification.
- Final handoff & Sentinel notification.
