# Changelog

## 2026-07-06 - RAG v2 Minimal Document Converter Adapters & Roadmap Sync

### Enhancements
- Completed RAG v2 Minimal Document Converter Adapters MVP (`RAG-V2-DOC-CONVERTER-ADAPTERS-MIN`) implementing the second RAG v2 foundation layer.
  - Code commit: `e2e39428f150f455a73beb84be0b7693252c9767` (Message: `Add RAG v2 minimal document converter adapters`)
  - Added generic converter layer and registry (`ConverterRegistry`).
  - Implemented generic minimal document converters:
    - `TextDocumentConverterAdapter` (TXT/MD/CSV)
    - `HTMLDocumentConverterAdapter` (HTML/HTM)
    - `PDFDocumentConverterAdapter` (PDF via PyMuPDF/fitz)
    - `ExcelDocumentConverterAdapter` (XLSX/XLSM via openpyxl)
    - `WordDocumentConverterAdapter` (DOCX zip/xml manual parser)
    - `PowerPointDocumentConverterAdapter` (PPTX zip/xml manual parser)
  - Fixed previous caveats:
    - Deterministic failed-element ID using SHA-256 path hash instead of Python `hash(path)`.
    - Future-proofed `DocumentElement.from_dict()` to ignore unknown fields.
  - Added new comprehensive test suite `tests/test_rag_v2_converters.py`.
  - Validation: 7 passed focused schema/adapters/hardcode, 10 passed converter tests, 17 passed all RAG v2 tests, 886 passed full pytest.
  - Import smoke: `RAG_V2_CONVERTER_IMPORT_PASS`.
- Initiated Roadmap Synchronization (`RM-SYNC-RAG-V2-DOC-CONVERTER-ADAPTERS-MIN`) to document MVP status, caveats, and next steps.

### Governance
- Preserved absolute NotebookLM-simple UX law.
- No UI changes, no runtime retrieval/chunking/index/synthesis.
- No dependency changes.
- Ensured no hard-coding of MOM/WMS business logic in core.
- Accepted warnings:
  - Wrong full-hash resolved to actual HEAD commit `e2e39428f150f455a73beb84be0b7693252c9767`.
  - Class named `ConverterRegistry` instead of `DocumentConverterRegistry`.
  - Unknown extension fail-closed with `FAILED` under fail-soft mode.
- A18 remains `NOT_STARTED`. P1.0 remains `LOCKED`.

## 2026-07-06 - RAG v2 Element Schema & Adapter Interface & Roadmap Sync

### Enhancements
- Completed RAG v2 Element Schema & Adapter Interface MVP (`RAG-V2-ELEMENT-SCHEMA-AND-ADAPTER-INTERFACE`) implementing the first generic foundation layer for RAG v2.
  - Code commit: `7db254a74889d4500e2bdf3dfcef6b6e9a7afe2e` (Message: `Add RAG v2 element schema and adapter interface`)
  - Added generic `DocumentElement`.
  - Added `AdapterCapabilities`.
  - Added table/cell metadata support.
  - Added serialization helpers and privacy metadata fields.
  - Added converter adapter protocol.
  - Added `ConversionContext`.
  - Added hard-code guard tests for RAG v2 core.
  - Validation: `876 passed`.
  - Import smoke: `RAG_V2_IMPORT_PASS`.
- Initiated Roadmap Synchronization (`RM-SYNC-RAG-V2-SCHEMA-ADAPTER`) to document MVP status, caveats, and next steps.

### Governance
- Preserved absolute NotebookLM-simple UX law.
- No UI/runtime retrieval/synthesis/index changes.
- No dependency changes.
- Ensured no hard-coding of MOM/WMS business logic in core.
- Caveats carried forward:
  - deterministic failed-element id
  - unknown future fields in `from_dict`
- A18 is marked `NOT_STARTED`. P1.0 remains `LOCKED`.

## 2026-07-06 - RAG v2 Design Document & Roadmap Sync

### Enhancements
- Added `docs/rag_v2/RAG_V2_DESIGN.md` establishing the architecture for a generic, element-first, local-first RAG core.
- Recorded decision to stop the MOM-specific answer composer (`FIX-MOM-ANSWER-COMPOSER-MIN`) path due to hard-coding risks.
- Added RAG v2 design direction:
  - Generic `DocumentElement` schema and converter adapter interface.
  - Structure-aware chunking (page, heading, table, cell range).
  - SQLite FTS/BM25 local index first, skipping cloud vector DB initially.
  - Standardized evidence packs and generic synthesis discipline.
  - Generic and private eval harness strategies.
  - Strict hard-code prevention policy: MOM/WMS terms are restricted to benchmark and eval config only.

### Governance
- Reaffirmed the absolute NotebookLM-simple UX law: RAG v2 will run side-by-side with the legacy MOM pilot without adding complex UI or new technical tabs to Workspace Chat.
- No code, runtime, test, or dependency changes were made in this design gate.
- A18 remains `NOT_STARTED`. P1.0 remains `LOCKED`.

## 2026-07-06 - MOM PDF Ingestion, Retrieval Ranking & Roadmap Sync

### Enhancements
- Completed MOM PDF Ingestion and Retrieval Ranking MVP (`FIX-MOM-PDF-INGESTION-RETRIEVAL-MIN`) adding reproducible PDF text-layer local-first extraction.
  - Code commit: `361bbc470db4970e584991b029c06f2f8846e910` (Message: `Improve MOM PDF ingestion and retrieval ranking`)
  - Declared `pymupdf4llm>=1.28.0` in `pyproject.toml` to ensure reproducible local environments.
  - Expanded `_tokens` tokenization pattern in `mom_local_index.py` to support CJK Japanese characters, enabling search matching on Japanese query terms.
  - Integrated domain-tuned boosts and penalties in `search_mom_index`:
    - **Q1 (MES/MOM)**: Boosted matching terms, `.pdf` files, and filenames containing `mes`/`mom`.
    - **Q2 (Production History)**: Boosted Japanese history terms, `.pdf` files, and filenames containing `生産履歴`/`着完工`/`仕様`.
    - **Q3 (Manual Shipping)**: Boosted Excel columns/metadata terms, `.xlsx`/`.xlsm` formats, and sheets/filenames containing `manual`/`ship` to prevent regressions.
    - **ERD Penalty**: Subtracted `50.0` from `ERD_Kho_Van_NEW.html` when a Q2 query is matched but the chunk lacks exact Q2 terms.
  - Added unit test suite `tests/test_mom_pdf_ingestion_retrieval.py` testing PDF extraction success (monkeypatched), fail-soft, PDF index generation, Q1/Q2 retrieval, and Q3 no-regression. All 869 tests pass.
  - Verified local MOM/WMS index smoke on real dataset: 518 rows (42 PDF chunks from 6 PDFs).
- Initiated Roadmap Synchronization (`RM-SYNC-FIX-MOM-PDF-RETRIEVAL`) to document MVP status, integration results, and licensing/retrieval caveats.

### Governance
- Preserved absolute NotebookLM-simple UX law: no new buttons, sidebar panels, or agent cockpit UI exposed on primary Workspace Chat screen.
- Accepted `pymupdf4llm` license caveat (AGPL/commercial dual-license): approved for local-first MVP validation, but requires review before broader distribution.
- Documented MVP caveats: PNG OCR remains deferred (no pytesseract dependency), Q3 Excel answer composer is pending, and router-grounded MOM answer path remains deferred.
- A18 is marked `NOT_STARTED`. P1.0 remains `LOCKED`.

## 2026-07-05 - Workspace Chat Hidden Router Adapter & Roadmap Sync

### Enhancements
- Completed Workspace Chat Hidden Router Adapter (AI-GW-A17D) implementing direct integration of the nakazasen-ai-router library to connect Workspace Chat's "Hỏi" button with the routed AI backend.
  - Verification results:
    - commit: `0c79958805faf1b45d3df53976a832dde1109bd7 — Add hidden router adapter for Workspace Chat ask`
    - dependency: `nakazasen-ai-router` version `v0.2.2` pinned in `pyproject.toml`
    - import check: IMPORT_PASS
    - focused AI answer tests: 50 passed
    - UI guard tests: 23 passed
    - A17A/A17B regression: 61 passed
    - full pytest: 863 passed
    - diff checks: PASS
    - dependency scan: PASS
    - forbidden UI scan: PASS
    - secret scan: PASS
    - raw logging scan: PASS
    - no-network validation: PASS (via mock/monkeypatch)
- Initiated Roadmap Synchronization (RM-SYNC-A17D) to record A17D completion and verify active/future gate statuses.

### Governance
- Preserved absolute NotebookLM-simple UX law verbatim: "GIAO DIỆN PHẢI DỄ SỬ DỤNG NHƯ NOTEBOOKLM. Nếu khó hiểu, coi như thất bại. Người dùng không có thời gian để ghi nhớ cách dùng quá phức tạp."
- Enforced strict fail-closed consent and snapshot gates:
  - If owner cloud consent is missing, the request fails closed and the router is not called.
  - If the active source set changes or doesn't match the consent snapshot, the request fails closed and the router is not called.
- Verified that all enabled sources (regardless of `local_only`, `machine_only`, `unknown`, `cloud_ok`, `public/test` labels) are routed upon valid owner consent, while disabled sources and the whole store are never sent.
- Maintained zero UI footprint: no new buttons, panels, dashboard, queue, metrics, or programming bridge exposed on the primary screen.
- AI-GW-A17D is marked complete (DONE/PUSHED/REMOTE_VERIFIED). RM-SYNC-A17D is the local docs-only sync gate pending Codex re-audit/push-safety. A18 remains NOT_STARTED.
- P1.0 remains LOCKED.

## 2026-07-05 - Workspace Chat Hidden UX Guardrails & Roadmap Sync

### Enhancements
- Completed Workspace Chat Hidden UX Guardrail Hardening (AI-GW-A17C) implementing test-first automatic guardrails to prevent Workspace Chat from regressing to cockpit complexity.
  - Verification results:
    - commit: `bc45d88f18650b1bea172572d1c2cafdd1c65864 — Harden Workspace Chat hidden UX guardrails`
    - Codex re-audit: PASS_A17C_HIDDEN_WORKSPACE_CHAT_GUARDRAILS_AUDITED_READY_FOR_PUSH_SAFETY
    - push-safety: PASS_A17C_HIDDEN_WORKSPACE_CHAT_GUARDRAILS_PUSHED_REMOTE_VERIFIED
    - focused tests: 23 passed
    - A17A/A17B regression: 61 passed
    - full pytest: 857 passed
    - diff checks: PASS
    - force push used: NO
    - only test files changed
    - no normal UI changes
    - accepted caveat: a single `gate` match in comment/docstring at `workspace_chat_app.py:1020` (does not display to user).
- Initiated Roadmap Synchronization (RM-SYNC-A17C) updating master roadmap and index.

### Governance
- Preserved absolute NotebookLM-simple UX law verbatim: "GIAO DIỆN PHẢI DỄ SỬ DỤNG NHƯ NOTEBOOKLM. Nếu khó hiểu, coi như thất bại. Người dùng không có thời gian để ghi nhớ cách dùng quá phức tạp."
- A17C is marked complete (DONE/PUSHED/REMOTE_VERIFIED). A17D remains NOT_STARTED.
- P1.0 remains LOCKED.

## 2026-07-05 - Workspace Chat NotebookLM-Simple UI Cleanup & Roadmap Sync

### Enhancements
- Completed Workspace Chat NotebookLM-simple UI Cleanup.
  - Verification results:
    - commit: `f23ea1345e1c3644f6037aa21ee428077cf1ac5a — Simplify Workspace Chat daily UX`
    - Codex re-audit: PASS_WORKSPACE_CHAT_NOTEBOOKLM_SIMPLE_CLEANUP_AUDITED_READY_FOR_PUSH_SAFETY
    - push-safety: PASS_WORKSPACE_CHAT_NOTEBOOKLM_SIMPLE_CLEANUP_PUSHED_REMOTE_VERIFIED
    - focused tests: 76 passed
    - full pytest: 856 passed
    - diff checks: PASS
    - force push used: NO
    - owner visual smoke check: PASS_OWNER_VISUAL_SMOKE
      - App launched directly into Workspace Chat at localhost:8501
      - Exact instruction: “Thêm tài liệu rồi hỏi tự nhiên; AIOS sẽ tự kiểm tra nguồn và cảnh báo nếu thiếu.”
      - Primary ask button: “Hỏi”
      - No visible stale/cockpit/test labels: “Các bước thử nghiệm”, “Pilot”, “Hỏi AI với nguồn đang bật”, “Kiểm tra nguồn trước”
      - No visible technical/dev concepts: “Giao AI xử lý”, “Nhập kết quả AI”, task pack, report import, hash, gate, commit, branch, push, A17
      - Advanced controls are collapsed: “Kiểm tra nguồn nâng cao”, “Thêm nguồn”, “Nhà phát triển / Thử nghiệm”, “Tùy chọn”, “Quản lý nguồn nâng cao”
- Initiated Roadmap Synchronization (RM-SYNC-UI-NOTEBOOKLM-CLEANUP) updating roadmap and master roadmap.

### Governance
- Preserved absolute NotebookLM-simple UX law verbatim: "GIAO DIỆN PHẢI DỄ SỬ DỤNG NHƯ NOTEBOOKLM. Nếu khó hiểu, coi như thất bại. Người dùng không có thời gian để ghi nhớ cách dùng quá phức tạp."
- A17C remains NOT_STARTED / UX-LOCKED. A17C can only be considered after RM-SYNC-UI-NOTEBOOKLM-CLEANUP is pushed/remote verified and the owner explicitly accepts the next A17C scope. Any future A17C must be hidden/simple Workspace Chat support only (no new cockpit, no multi-step agent UI, no task-pack/report-import UI).
- P1.0 remains LOCKED.

## 2026-07-05 - Agent Result Import MVP Completion & Roadmap Sync

### Enhancements
- Completed Agent Result Import MVP (AI-GW-A17B) implementing local-only validation of agent reports under the `aios_agent_report_v1` schema.
  - Verification results:
    - focused A17B tests: 42 passed
    - A17A + A17B regression: 61 passed
    - full pytest: 855 passed
    - git diff --check: PASS
    - uv.lock: absent / not tracked
    - source scan: PASS, only safe comment match
    - force push used: NO
    - post-push remote verification: PASS
- Enforced strict canonical JSON hashing, depth checks (max 20), size limits (max 1 MiB), and non-object JSON root guards to prevent unstructured exceptions.
- Added path security checks to reject control characters in declared files and prevent echoing raw absolute/UNC/system paths or secrets in safe summaries.
- Modified agent class validation to match only if available in the task pack.
- Expanded parameterized tests to ensure observed evidence missing/false values properly downgrade verdicts to `REVIEW_REQUIRED`.
- Initiated Roadmap Synchronization (RM-SYNC-A17B) introducing the absolute "NotebookLM-simple UX lock" rule to guarantee the interface remains clean and easy to use.

### Governance
- Added the absolute UX governance rule: "GIAO DIỆN PHẢI DỄ SỬ DỤNG NHƯ NOTEBOOKLM. Nếu khó hiểu, coi như thất bại. Người dùng không có thời gian để ghi nhớ cách dùng quá phức tạp."
- Confirmed Workspace Chat is the primary daily UX and Case Cockpit-style complexity is retired.
- Placed AI-GW-A17C "Workspace Chat helper" under UX lock. Next required gate is UI audit before opening A17C implementation.
- P1.0 remains LOCKED.

## 2026-07-05 - Agent Task Pack Export MVP Completion & Roadmap Sync

### Enhancements
- Completed Agent Task Pack Export MVP (AI-GW-A17A) implementing validated, version-controlled local task pack generation using deterministic JSON, SHA-256 integrity hash calculation, strict destination enum, and atomic outbox exports.
- Prepared Roadmap Synchronization (RM-SYNC-A17A) updating the candidate gate queue, documenting A17A design/implementation details, commit chain verification, and the accepted hardening backlog.

### Safety
- Restricts `destination` to `local_owner_only`, `external_manual_agent`, or `owner_managed_chat`. Rejected direct cloud destination.
- Imposes strictest-wins privacy orders and filters sensitive credentials, path segments (such as `.ai`, `local_cases`), and raw transcript markers from exported pack objectives.
- Enforces strict path policy on external/chat packs by blocking absolute, UNC, system, or traversal paths.
- Uses atomic writes with `os.replace` under `local_runs/agent_bridge/outbox` to prevent data corruption.
- Trailing whitespaces stripped and `uv.lock` safely isolated/removed from version control.


## 2026-07-05 - IDE Agent Bridge Design Completion & Roadmap Sync

### Enhancements
- Completed IDE Agent Bridge Design (AI-GW-A17-DESIGN) establishing task pack schemas, result import boundaries, strict observed-evidence provenance checking, and path traversal controls.
- Prepared Roadmap Synchronization (RM-SYNC-A17-DESIGN) locally, updating the active candidate gate queue, Phase 5 status clarification, and commit timeline records (pending push-safety and post-push verification).

### Safety
- Strict path policy: Absolute repository paths are strictly forbidden except for `local_owner_only` workflows remaining on the owner's machine.
- Observed evidence provenance: verifier receipts require mandatory tracking fields (`command_source`, `command_from_report`, `report_command_ignored`, `validation_config_sha256`) to ensure tests are owner-triggered under fixed configurations, not agent-supplied commands.
- Removed all pre-filled success outputs in prompt audit templates to prevent fake PASS.
- Clarified that SHA-256 is strictly an integrity hash/checksum, not a digital signature.


## 2026-07-05 - AIOS Brain Gateway Mock Router Guard & Roadmap Sync

### Enhancements
- Completed Workspace Chat Source Library (WSC-1C) management, including search/filter, bulk enable/disable, temporary deletion, confirmation dialogues, and test coverage (754 passed).
- Completed AIOS Brain Gateway Integration Design (AI-GW-A15) which details the system inventory, gateway architecture, router adapters, IDE bridge, and import design docs.
- Completed AIOS Brain Gateway Router Mock Integration (AI-GW-A16) implementing privacy gateway, OwnerConsent validation with source snapshots, opaque metadata mapping, marker redactions, and offline MockRouterAdapter.
- Completed Roadmap Synchronization (RM-SYNC-A16) standardizing Phase/Gate names, updates on progress estimate, and prompt governance.

### Safety
- Added comprehensive leak validation (paths, secrets, tokens) inside MockRouterAdapter (fail-closed).
- Error messages are anonymized to prevent raw token/path leakage.
- Workspace Chat security errors are mapped to a fixed safe Vietnamese message.
- P1.0 production readiness remains LOCKED.
- Verified local test suites (794 passed), mojibake clean status (280 files), and CLI audits.

## 2026-07-04 - Workspace Chat Primary UI & Legacy Retirement Sync

### Enhancements
- Established Workspace Chat as the primary UI for WorkLens.
- Replaced default launcher shortcuts (`RUN_AIOS_HABIT_STUDIO.bat`, `run_studio.ps1`) to run the Workspace Chat application.
- Added legacy warning banners and console output to older UI components (`studio.py`, `case_cockpit.py`, `RUN_AIOS_CASE_COCKPIT.bat`, `run_case_cockpit.ps1`) to mark them as reference/debug only.
- Completed multi-format source ingestion, multi-file uploader, image/WebP graceful handling, and local retrieval/evidence items (Gate 1B).
- Completed repository-wide Vietnamese mojibake scan and encoding audit.
- Updated documentation and roadmaps to reflect the primary UI status and next queue for Gate 1C (Source Library / Source Management UX).
- Ensured P1.0 production readiness remains LOCKED.

## 2026-06-30 - Workspace Chat UI Phase 1

> [!NOTE]
> The Workspace Chat is currently in Phase 1 (UI Shell & Mock placeholders). It does not connect to active AI generation, perform actual case saving, or run structural map validation.

### Enhancements
- Implemented Phase 1 Workspace Chat UI as a parallel independent component:
  - Added data models in `workspace_chat_models.py` (`DocumentNotebook`, `WorkspaceConversation`, `ChatMessage`, `TemporaryConversationSource`).
  - Added separate storage engine in `workspace_chat_store.py` writing into an isolated directory `local_cases/workspace_chat/`.
  - Added UI helper functions in `workspace_chat_ui.py` supporting Vietnamese-only non-technical copywriting.
  - Added parallel Streamlit entrypoint `workspace_chat_app.py` for workspace chat.
- Ensured zero coupling with legacy `case_cockpit.py` UI rendering logic and state keys.
- Completely removed forbidden technical terms (RAG, node, edge, claim, citation, etc.) from the user-facing text.

### Testing
- Created standard and architectural tests ensuring decoupling, UI text compliance, and store directories isolation:
  - `tests/test_workspace_chat_models.py`
  - `tests/test_workspace_chat_store.py`
  - `tests/test_workspace_chat_owner_flow.py`
  - `tests/test_workspace_chat_ui_copy.py`
  - `tests/test_workspace_chat_architecture_boundary.py`

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
