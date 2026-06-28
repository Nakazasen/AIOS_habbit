# Changelog



## 2026-06-28 - RAG Benchmark Harness

### Enhancements
- Added RAG benchmark harness `rag_benchmark.py`.
- Measures retrieval/evidence quality only with deterministic metrics.
- Supports 20Q, 50Q, 100Q, and custom benchmark tiers.

### Safety
- No provider or cloud calls.
- No NotebookLM parity claim.
- No runtime benchmark outputs committed.

## 2026-06-28 - IDE/Model Answer Bridge Foundation

### Enhancements
- Added manual IDE/model bridge foundation in `ide_bridge.py`.
- Added prompt pack export from evidence pack.
- Added paste-back answer record model.
- Added local_only export blocking and explicit redacted/cloud-safe policies.

### Safety
- No provider/API automation.
- No cloud calls.
- No vector DB/graph DB/reranker.
- No NotebookLM parity claim.

## 2026-06-28 - RAG Evidence Pack Foundation



### Enhancements

- Added evidence pack builder for RAG Engine v2 in `rag_evidence.py`.

- Added citation IDs, source references, score details, coverage summary, and missing evidence warnings.

- Preserved privacy mode and external-send guard metadata through the evidence pack.

- Maintained zero dependency on vector databases, graph databases, or cloud embeddings for local retrieval.

- No answer composer replacement yet.



## 2026-06-28 - Local FTS Search Foundation



### Enhancements

- Added local SQLite FTS/BM25 search foundation in `rag_search.py`.

- Added metadata filters (privacy_mode, file_type, source_title, page_numbers, sheet_names).

- Safe fallback mechanism implemented when SQLite FTS5 is not available.

- Added adapter `build_search_index_from_rag_chunks` to `notebook_index.py`.

- Maintained zero dependency on vector databases, graph databases, or cloud embeddings for local retrieval.



## 2026-06-28 - RAG v2 and Agent Harness Research



### Research

- Added docs-only architecture research for `AIOS-RAG-AGENT-HARNESS-0`.

- Audited current ingest, retrieval, answer, provider route, and missing IDE/model bridge capabilities.

- Compared public RAG/document intelligence and agent harness patterns without copying source code.

- Designed Phase 4 Retrieval Engine v2 and Phase 5 IDE Answer Bridge architecture.

- Confirmed P1.0 remains locked and NotebookLM parity is not claimed.



### Next Gates

- Recommended next order: `AIOS-RAG-INGEST-1`, `AIOS-RAG-SEARCH-1`, `AIOS-RAG-EVIDENCE-PACK-1`, `AIOS-IDE-BRIDGE-1`, `AIOS-RAG-BENCHMARK-1`.

## 2026-06-28 - Roadmap Reposition around WorkLens Mission, RAG v2, and IDE Bridge



### Roadmap

- Repositioned AIOS as a local-first personal work memory operating system, not only a document Q&A app.

- Added explicit 10-phase roadmap from Vision/Governance through RAG Engine v2, IDE/model bridge, case memory at scale, work stream map, senior learning memory, production traceability foundation, and locked P1.0 readiness.

- Set current position to the end of Phase 3, before Phase 4 RAG Engine v2 and Phase 5 IDE/model bridge.

- Marked NotebookLM parity as not achieved and P1.0 as locked.



### Strategy

- Documented why model calls are only one part of answer quality: parser, index, retrieval, rerank, evidence pack, context, model, privacy guard, and route log all matter.

- Added a future research queue for public RAG and agent-harness patterns only; no leaked/proprietary code copying.

- Added immediate next gates `AIOS-RAG-AGENT-HARNESS-0`, `AIOS-RAG-INGEST-1`, `AIOS-RAG-SEARCH-1`, `AIOS-RAG-EVIDENCE-PACK-1`, and `AIOS-IDE-BRIDGE-1`.

## 2026-06-28 - Roadmap Review after Normal Provider UI Pilot



### Validation

- Marked the one-screen **Làm việc hằng ngày** flow as stable enough for guided daily pilot use.

- Recorded the normal-document provider UI pilot as passed with DeepSeek, fallback disabled, visible route summary, and Q&A-to-Case creation.

- Reconfirmed company/mật protection through direct negative checks: no cloud/provider call for protected mode.



### Roadmap

- Added next decision gate `AIOS-P1-READINESS-DECISION-1` for owner review before opening any P1.0 checklist.

- Kept P1.0 closed; current state is daily-pilot ready, not production-ready.



### Known Warnings

- Browser automation could not type Vietnamese accents reliably.

- Notebook name entry can append to the default value instead of replacing it.

- Answer, route, and provider metadata may require scrolling.

- Q2/Q3 browser automation sometimes needed repeated focus/submit attempts.

- Selecting a newly created case from a long dropdown can require scrolling.

- MOM UI safety was not rerun in the last browser pilot, although tests and direct safety checks pass.



## 2026-06-27 - Real Provider Routing Foundation and Daily Pilot



### Added

- Added safe real-provider support for normal documents (`Tài liệu thường`) through the AI router.

- Added provider health, key masking, cooldown, and key-rotation foundation.

- Added `.gitignore` guard for local API key files including `API Key.txt`, `API*.txt`, `.env`, and provider config files.



### Changed

- Fixed the custom normal-notebook UI route so `Tự động chọn AI tốt nhất` uses the provider router instead of the old local-only path.

- Consolidated Vietnamese route-log visibility for provider decisions, external-send status, fallback status, and provider used.



### Validation

- Verified DeepSeek with synthetic public normal-document pilots.

- Verified MOM/company data remains blocked from external providers by tests, direct audits, and negative pilot checks.

- Verified `API Key.txt` remains ignored and untracked; no real key is committed.



### Known Warnings

- Browser/DOM evidence is partial in some runs because browser-agent automation was unstable.

- Q&A-to-Case currently preserves answer, source refs, and safety, but does not persist route summary as a dedicated case field yet.

- Provider key-rotation foundation exists, but real multi-key rotation is not fully field-tested.

- This is a usable foundation for normal documents, not P1.0 production readiness.



## 2026-06-21 - Notebook Intelligence & Bridge Persistence (M1.8A - M1.8D)



### Added

- Created `src/aios_habit/notebook_index.py` supporting localized source document chunk indexing (~1200 chars) and keyword/phrase matching (M1.8A).

- Created `src/aios_habit/notebook_qa.py` compiling Q&A contexts and Study Pack prompts (M1.8A).

- Created `src/aios_habit/notebook_graph.py` creating visual structural relation graphs (Mermaid format) (M1.8A).

- Created `src/aios_habit/llm_client.py` containing a lightweight urllib-based OpenAI-compatible API client (M1.8B).

- Created `src/aios_habit/notebook_bridge.py` supporting parsing NotebookLM output and converting JSON graphs to Mermaid format (M1.8C).

- Created `src/aios_habit/notebook_import_store.py` providing a JSONL-based persistence layer for saved NotebookLM imports (M1.8D).

- Added comprehensive unit test suites:

  - `tests/test_notebook_intelligence.py` (M1.8A)

  - `tests/test_notebook_in_app_qa.py` (M1.8B)

  - `tests/test_llm_client.py` (M1.8B)

  - `tests/test_notebook_bridge.py` (M1.8C)

  - `tests/test_notebook_import_store.py` (M1.8D)



### Changed

- Integrated in-app Q&A and 4 Truth Modes (Local, Cloud-safe, NotebookLM Bridge, Prompt Copy Fallback) in `case_cockpit.py` Tab 3 (M1.8B & M1.8C).

- Hard gated cloud targets to strictly prevent `local_only` raw data leakage, displaying UI warnings and blocking API execution (M1.8B & M1.8C).

- Enabled pasting, formatting, and rendering of parsed JSON structures and Mermaid diagrams inside Case Cockpit (M1.8C).

- Enabled saving, listing, viewing, and deleting saved NotebookLM imports in the Knowledge Notebook cockpit area (M1.8D).

- Integrated visual graph rendering of saved NotebookLM imports in Tab 5 (Bản đồ) (M1.8D).

- Synchronized roadmap and governance rules to prevent drift and locked M1.8D-R (M1.8D-R).



### Security

- Capped chunk indexing, restricted LLM execution context, and ensured all persistent imports default to `local_only` and `draft` status (M1.8A - M1.8D).





## 2026-06-20 - M1.7B Path Containment Hotfix



### Security

- Fixed notebook source path traversal risk in Knowledge Notebook source storage.

- Validated strict `notebook_id` allowlist policy (`^[a-zA-Z0-9_-]+$`).

- Enforced `resolve()` + `is_relative_to()` containment for notebook asset directories and source file destinations.

- Replaced legacy `startswith()` path containment in case upload/audit paths.

- Capped source `preview_text` at 1000 characters after extraction.



### Tests

- Added regression test for malicious notebook IDs, including traversal, absolute paths, Windows drive-style paths, and nested path separators.

- Codex retest passed with `PASS_M1_7B_BLOCKER_FIXED`.



## 2026-06-21 - Workspace, Notebook, and Navigation Simplification (M1.7)



### Added

- Created `src/aios_habit/workspace_models.py` defining `Workspace` and `KnowledgeNotebook` models and local storage.

- Created `src/aios_habit/source_ingest.py` supporting safe document ingestion under `local_cases/notebook_assets/` using `Path.is_relative_to()` path containment checks.

- Created user documentation `docs/KNOWLEDGE_NOTEBOOK.md` outlining workspaces, notebooks, and source vs. evidence data separation.

- Created test suite `tests/test_workspace_notebook.py` covering model defaults, containment safety, and sentinel privacy leak protection.



### Changed

- Refactored `case_cockpit.py` sidebar navigation: reduced choice clutter by grouping pages into 5 main categories and using native Streamlit tabs inside the content area.

- Added a Workspace selector and management tools directly in the sidebar.

- Added Sổ tri thức (Knowledge Notebook) page enabling notebook creation and source document upload with preview parsing.

- Expanded `Case` model with `workspace_id` and `linked_notebook_ids` fields while maintaining 100% backward compatibility.

- Integrated linked notebook and source document reference sections in prompt compilations (`case_prompt.py`) and safety validation rules (`case_audit.py`).



## 2026-06-20 - Roadmap Governance Lock



### Added

- Locked AIOS WorkLens product doctrine.

- Defined AIOS as Personal Senior Work Intelligence System.

- Updated core loop: `Knowledge → Case → Evidence → Reasoning Map → Action / Communication → Outcome → Learning Memory → Better Work`.

- Added/updated 7 product layers.

- Clarified model/agent roles.

- Defined M1.7 as next gate.



## 2026-06-20 - Case Cockpit Privacy and Audit Hardening



### Added

- Created `src/aios_habit/case_prompt.py` for privacy-aware prompt compilation.

- Created `src/aios_habit/case_audit.py` to run comprehensive, testable audits on case state, prompts, and local paths.

- Added comprehensive test suite `tests/test_case_cockpit_hardening.py` covering prompt privacy, xlsx ingest, audit rules, Mermaid label escaping, store roundtrips, and launcher command checks.



### Changed

- Integrated prompt and audit helpers into `case_cockpit.py`.

- Hardened `case_graph.py` with `safe_mermaid_label()` to escape quotes, brackets, braces, and newlines.

- Hardened `case_ingest.py` with `safe_asset_filename()` to filter name path separators, normalize dangerous characters, and prefix with a unique timestamp to prevent overwrite collisions.

- Applied Streamlit-level input validation preventing empty titles, empty notes, and empty chat logs.



### Security

- Excluded `local_only` evidence from cloud targets (`gemini`, `gpt`, `copilot`, `notebooklm_safe`) by default.

- Added path containment assertion in file upload to block directory traversal attacks.



## 2026-06-20 - WorkLens Governance and Inheritance Audit



### Added

- Product north star for AIOS WorkLens.

- Master roadmap with 10 phase gates.

- Migration policy and inheritance map for 4 repositories.

- Monday pilot checklist and Case Cockpit acceptance criteria.

- Read-only inheritance audit reports for ABW_NVIDIA_FUSION_CONTROL, skill-Anti-brain-wiki_note, and Nvidia.



### Changed

- Project handover reframed AIOS_habbit as central WorkLens / Case Cockpit product repo.



### Security

- Reaffirmed local-first public safety and no blind code/data copying.



## 2026-06-20 - AIOS Habit Studio Local UI



### Added

- Streamlit-based Web UI (`aios-habit-studio`) to provide a graphical interface over the CLI tools.

- Launcher scripts `RUN_AIOS_HABIT_STUDIO.bat` and `scripts/run_studio.ps1`.

- UI tabs for Dashboard, Projects, Evidence, Memory, Review Queue, Profiles, Export, Audit, Handover, and Settings.

- Documentation for the Studio UI (`docs/STUDIO_UI.md`).



## 2026-06-20 - AIOS Habit Local Platform Completed



### Added

- Python package under `src/aios_habit`.

- CLI `aios-habit` with status, discover, evidence, memory, extract, workflow, decision, profile, export, audit, phase, and handover commands.

- Pytest suite under `tests/`.

- Documentation under `docs/`.

- Phase reports and final audit/handover generators.

- AI export packs for generic, GPT, Gemini, Claude and Grok.



### Changed

- Roadmap updated to Phase 0-9 execution model.

- Phase 0 checklist closed as PASS after validation.



### Security

- Export excludes source conversation archives by default.

- Audit detects common secret patterns and verified memory without evidence.



### Validation

- `py -3 -m pytest`: PASS.

- CLI smoke commands: PASS.

- `aios-habit audit`: PASS after implementation validation.



### Handover

- `PROJECT_HANDOVER.md` and `09_handover/final_handover.md` generated.



## 2026-06-20 - Public-safe MVP hardening



### Added

- Modular CLI implementation, real phase gates, CI workflow, and expanded tests.



### Security

- Hardened gitignore for private runtime data and export packs.



### Validation

- py -3 -m pytest: 16 passed.







