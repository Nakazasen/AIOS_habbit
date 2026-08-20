# Project: AIOS_habbit MOM Forensic Code Audit & Production Readiness Assessment

## Architecture & System Overview
Target components under forensic investigation:
- `src/aios_habit/` (Core MOM indexing, vector store, document inventory, parsing logic, extraction)
- `scripts/` (`mom_benchmark.py`, `mom_benchmark_gate.py`, `battle_notebooklm_rag_v2.py`, evaluation scripts)
- `tests/` (Test suites, mocks, fixtures, test data)
- Documents & indices: `data/`, `real_doc_inventory.py`, `mom_local_index.py`, `mom_coverage.py`

## Feature Inventory (Investigation Targets)
| # | Component | File Path(s) | Focus Area | Assigned Subagent | Status |
|---|---|---|---|---|---|
| F1 | MOM Document Inventory & Parsing | `src/aios_habit/real_doc_inventory.py`, `src/aios_habit/mom_coverage.py`, `src/aios_habit/parsers/` | Forensic check for PDF/Excel/Word/TXT parser reality vs mock/fake parsing | explorer_1 | PLANNED |
| F2 | MOM Local Index & Vector Storage | `src/aios_habit/mom_local_index.py`, embedding models, chunking, storage | Forensic check for real embeddings/search vs canned retrieval results | explorer_1 | PLANNED |
| F3 | MOM Benchmark & Evaluation Gates | `scripts/mom_benchmark.py`, `scripts/mom_benchmark_gate.py`, `tests/` | Forensic check for canned answers, hardcoded metrics, artificial scoring heuristics | explorer_2 | PLANNED |
| F4 | MOM Battle Scripts & End-to-End RAG | `scripts/battle_notebooklm_rag_v2.py`, integration pipelines | Forensic check for real vs simulated benchmark execution against NotebookLM/RAG | explorer_3 | PLANNED |
| F5 | Production Readiness & Feasibility | All MOM components & dependencies | Scalability on large docs, format support, offline/online dependencies, hallucination risks, edge cases | explorer_3 & worker_1 | PLANNED |
| F6 | Master Audit Report Generation | `08_audit/MOM_HARDCODE_AND_PRODUCTION_READINESS_AUDIT.md` | Synthesize Executive Summary, Component Breakdown, Readiness Evaluation, Roadmap | worker_1 | PLANNED |
| F7 | Multi-Agent Review & Audit Gate | Reviewers, Challengers, Forensic Auditor | Validate all citations, line numbers, verify zero hallucination in audit report | reviewer_1, reviewer_2, challenger_1, challenger_2, auditor_1 | PLANNED |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Forensic Survey & Codebase Investigation | 3 Parallel Explorers investigating MOM indexing, benchmark/gates, and battle/RAG pipelines | None | IN_PROGRESS |
| M2 | Report Synthesis & Draft Generation | Worker writes `08_audit/MOM_HARDCODE_AND_PRODUCTION_READINESS_AUDIT.md` with complete evidence tables | M1 | PLANNED |
| M3 | Comprehensive Multi-Agent Verification Gate | Reviewers, Challengers, and Forensic Auditor verify evidence & report integrity | M2 | PLANNED |
