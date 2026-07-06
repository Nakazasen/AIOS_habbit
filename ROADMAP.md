# AIOS WorkLens High-Level Roadmap Index

AIOS WorkLens / AIOS_habbit là một **hệ điều hành trí nhớ công việc cá nhân, local-first**: biến tài liệu, Excel, ảnh, log, chat, email, AI output và sự việc hằng ngày thành tri thức tái sử dụng theo vòng:

```text

Case → Evidence → Map → Action → Learning → Memory

```

## Core Reference Documents

- **Product North Star & Doctrine:** [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md)

- **Master Roadmap & Governance:** [WORKLENS_MASTER_ROADMAP.md](WORKLENS_MASTER_ROADMAP.md)

- **Product Positioning:** [docs/AIOS_PRODUCT_POSITIONING.md](docs/AIOS_PRODUCT_POSITIONING.md)

---

## Repository State Policy

- Authoritative current HEAD/origin state must be verified by Git during each gate.
- This roadmap intentionally does not claim the hash of its own latest commit.
- Commit hashes recorded below are historical gate evidence, not self-updating current HEAD fields.

## Active Position

- Current phase: Phase 4 — Workspace Chat Foundation & AI Gateway Preparation.
- Latest closed implementation gate: FIX-MOM-PDF-INGESTION-RETRIEVAL-MIN — Improve MOM PDF ingestion and retrieval ranking — DONE / PUSHED / REMOTE_VERIFIED.
- Latest closed roadmap sync gate: RM-SYNC-FIX-MOM-PDF-RETRIEVAL — DONE / PUSHED / REMOTE_VERIFIED.
- Latest closed design gate: RAG-V2-DESIGN-DOC — Generic element-first local-first RAG core — DONE / LOCAL_DOC_READY.
- Current roadmap sync gate: RM-SYNC-RAG-V2-ROADMAP-AND-DESIGN-DOC — Sync Master Roadmap after RAG v2 Design — IN PROGRESS.
- Next candidate gate: Codex re-audit / push-safety of RM-SYNC-RAG-V2-ROADMAP-AND-DESIGN-DOC docs-only commit.
- Next implementation gate: RAG-V2-ELEMENT-SCHEMA-AND-ADAPTER-INTERFACE (after push-safety of design).
- MOM-specific composer (FIX-MOM-ANSWER-COMPOSER-MIN) is STOPPED due to hard-code risk.
- MOM/WMS remains benchmark/eval/private dataset only, not core logic.

### Recent verified gates / historical status labels
- KEY SETUP LOCAL — PASS
- REAL AI SMOKE — PASS
- OWNER UI SMOKE — PASS
- FIX-AIOS-MOM-WMS-RUNTIME-ENV — PASS
- HOME TEMP 52 DATASET battle — PASS_WITH_LIMITATIONS
- COMPANY 68 DATASET retrieval robustness — PENDING
- RAG-V2-RESEARCH-FIRST-ARCHITECTURE-AUDIT — PASS
- RAG-V2-DESIGN-DOC — PASS / LOCAL_DOC_READY
- RAG-V2 roadmap/design docs commit — LOCAL_COMMIT_READY_FOR_PUSH_SAFETY
- A18 — NOT_STARTED
- P1.0 — LOCKED
- IDE bridge — unopened

---

## NotebookLM-Simple UX Governance Law

### Absolute UX Law:
"GIAO DIỆN PHẢI DỄ SỬ DỤNG NHƯ NOTEBOOKLM. Nếu khó hiểu, coi như thất bại. Người dùng không có thời gian để ghi nhớ cách dùng quá phức tạp."

### UX Law Interpretation:
- Workspace Chat is the primary daily user experience.
- Do not recreate or reintroduce a complex Case Cockpit-style interface.
- Do not expose task pack, report import, hash, gate, commit, branch, push, or agent bridge concepts to normal users.
- A17A/A17B are backend/developer safety layers only.
- A17A/A17B must stay invisible in normal daily WorkLens usage.
- Any future A17C "Workspace Chat helper" must simplify the NotebookLM-like chat experience.
- A17C must not add visible multi-step workflow, cockpit, new sidebar complexity, or buttons such as "Giao AI xử lý" / "Nhập kết quả AI" unless explicitly approved by the owner after UX audit.
- If a proposed UI change requires the user to remember a complicated workflow, it fails.
- The product direction is: open Workspace Chat, add/select sources, ask questions naturally, receive grounded answers.
- Advanced safety checks must be automatic or hidden behind simple warnings.
- UI audit is mandatory before opening any UI-affecting A17C work.

---

### M1.13 — Owner Trial Pain Point Fixes

Status: DONE.

Exit criteria:

- pending requests visible in UI/helper;
- response.json import can be discovered automatically;
- Markdown paste fallback works with strict validation;
- request_id folder navigation reduced;
- Visual Map preview appears after save-back;
- tests pass;
- no unsafe content committed.

### M1.14A — Visual Map UI Reference Study

Status: DONE.

Scope:

- studied Obsidian, React Flow, Cytoscape.js, D3-force, and optional graph/citation UX patterns;
- translated proven patterns into an AIOS-specific, evidence-grounded, local-first Visual Map UI design;
- selected Streamlit table-first UI as the recommended next implementation path;
- did not implement UI, add dependencies, add a graph database, run benchmarks, open P1.0, or claim NotebookLM replacement/global parity.

Exit criteria:

- reference study document created;
- interaction decision document created;
- roadmap updated;
- validation and safety scan passed;
- only safe design docs committed.

### M1.14B — Visual Map UI Interaction Table-First Implementation

Status: DONE.

Scope:

- implemented table-first UI helper without heavy graph dependencies;
- updated Case Cockpit with interactive filtering and node/edge details;
- ensured missing evidence, risk, action, and learning panels are visible;
- kept visual graph generation local-first and privacy-safe;
- verified no NotebookLM/P1.0 overclaims.

Exit criteria:

- table-first UI helper exists
- Case Cockpit has interactive Visual Map section
- filters work
- node detail works
- edge reason works
- missing evidence/risk/action/learning panels visible
- safe exports remain safe
- tests pass
- safety scan passes
- no unsafe content committed
- no NotebookLM/P1.0 overclaim

## Mission and Non-goals

AIOS is:

- A local-first personal work memory operating system.

- A system for evidence-grounded work: Case, Evidence, Map, Action, Learning, Memory.

- A privacy-aware multi-model workbench that records evidence, route log, model/tool used and privacy mode.

AIOS is not:

- a chat backup;

- a simple RAG chatbot;

- only a NotebookLM clone;

- a production prediction engine;

- a cloud document upload tool;

- an LSU-only traceability system.

---

## Phase Roadmap

### Phase 0 — Vision & Governance

Status: DONE.

Scope:

- mission;

- local-first rules;

- no fake PASS;

- privacy constraints;

- roadmap guardrails.

### Phase 1 — Local Case Cockpit Foundation

Status: DONE.

Scope:

- case model;

- evidence;

- quick intake;

- handoff;

- learning card;

- audit gates.

### Phase 2 — Real Document / MOM Foundation

Status: DONE_WITH_WARNINGS.

Scope:

- MOM local ingest/index;

- 50Q benchmark;

- source refs;

- local-only guard;

- NotebookLM comparison baseline.

Warning:

- not NotebookLM-level semantic retrieval yet.

### Phase 3 — Provider Safety + Daily UI

Status: DONE_WITH_WARNINGS.

Scope:

- Vietnamese safety modes;

- provider catalog;

- route log;

- DeepSeek normal-doc UI pilot;

- one-screen daily flow;

- Q&A to Case route summary.

Warning:

- daily-pilot ready, not production-ready.

### Phase 4 — Workspace Chat Foundation & AI Gateway Preparation

Status: IN PROGRESS.

*Note: M1.x is an internal milestone stream under Phase 4, not a separate product phase.*

Scope:

- Ingest: `RAGChunk` and `RAGDocumentElement` with stable IDs (DONE `AIOS-RAG-INGEST-1`).

- Search: Local SQLite FTS/BM25 + fallback string search (DONE `AIOS-RAG-SEARCH-1`).

- Pack: Evidence pack builder, source scoring, and answer abstention (DONE `AIOS-RAG-EVIDENCE-PACK-1`).

- Rerank: Local semantic reranker (PENDING `AIOS-RAG-RERANK-1`).

- cloud embedding for company/mật;

- fake NotebookLM parity claim.

### Phase 5 — IDE / Strong Model Answer Bridge

Status: DONE_WITH_WARNINGS / FOUNDATION_DONE.

Clarification:

- Manual IDE answer/evidence bridge foundation exists: prompt/evidence pack export, paste-back answer import, model/tool name, evidence refs, route summary, and privacy guard.
- A17 docs-only design is now complete (AI-GW-A17-DESIGN is DONE/PUSHED/REMOTE_VERIFIED).
- Runtime repo-task bridge Task Pack Export MVP is now complete (AI-GW-A17A is DONE/PUSHED/REMOTE_VERIFIED).
- Runtime repo-task bridge Result Import MVP is now complete (AI-GW-A17B is DONE/PUSHED/REMOTE_VERIFIED).
- A17C is complete (DONE/PUSHED/REMOTE_VERIFIED). A17D is complete (DONE/PUSHED/REMOTE_VERIFIED).
- Phase 5 is therefore not fully complete as a runtime-controlled IDE Agent Bridge.

Scope:

- export prompt pack;

- use Codex/Gemini/Claude/GPT/Opus in external IDE/chat;

- paste-back answer;

- store model/tool name;

- store evidence refs;

- store route summary;

- privacy guard.

Not allowed yet:

- direct cloud call for company/mật;

- raw API keys in UI/logs;

- automatic agent edits without approval.

### Phase 6 — Case Memory at Scale

Status: LATER.

Scope:

- many-case search;

- case index;

- duplicate detection;

- cross-case lessons;

- timeline;

- tags/entities;

- find similar incident.

Warning:

- currently NOT_READY.

### Phase 7 — Work Stream Map / Knowledge Graph

Status: LATER.

Scope:

- work stream graph;

- case/evidence/action relation;

- lightweight graph first;

- no graph DB until proven necessary.

### Phase 8 — Senior Learning / Personal OS

Status: LATER.

Scope:

- senior learning memory;

- repeated workflow extraction;

- communication style;

- decision pattern;

- reusable prompts;

- AI-independent personal memory.

### Phase 9 — Production Traceability Foundation

Status: LATER.

Scope:

- generic unit traceability foundation;

- not LSU-only;

- LSU/Drum/DLP/Fuser/Scanner/MainBody/Other;

- fake CSV first;

- simple join/risk summary.

Forbidden:

- prediction engine;

- ML;

- production DB integration;

- long research branch.

### Phase 10 — P1.0 Production Readiness

Status: LOCKED.

Open only if:

- owner completes real daily scenario without agent assistance;

- RAG v2 benchmark passes;

- privacy audit passes;

- route log/case/evidence trace stable;

- docs/user guide ready;

- no secret/runtime commit risk.

---

## Why model call is only a small part

AIOS quality depends on the full chain: parser → index → retrieval → rerank → evidence pack → context → model → privacy guard → route log. A stronger model alone is not enough if parsing, chunking, retrieval, citations or privacy routing are weak. Free/low-tier models may be useful for simple public notes but are insufficient for complex documents. Strong models should be used safely through Phase 5 IDE/model bridge, with exported evidence packs, paste-back answers, model/tool name, route summary and privacy mode stored.

Future research should learn public patterns from RAGFlow, kotaemon, Microsoft GraphRAG, LightRAG, LlamaIndex, Haystack, Docling, Unstructured, OpenHands, Aider, Cline, Continue, Goose, Cognee, Letta/MemGPT, LangGraph and Semantic Kernel. Do not copy leaked/proprietary code.

## Next Gate Queue

Immediate:

- **RM-SYNC-A17D — Sync Master Roadmap after A17D Hidden Router** (IN_PROGRESS) — roadmap sync gate updating roadmap and changelog status after AI-GW-A17D hidden router adapter commit is pushed/remote verified.
- **AI-GW-A18 — NotebookLM Comparison Arena** (NOT_STARTED) — after A17 or later strategy decision.

Completed:

- **AI-GW-A17D — Hidden Router Adapter for Workspace Chat Ask** (DONE/PUSHED/REMOTE_VERIFIED) — direct integration of the nakazasen-ai-router library with Workspace Chat's "Hỏi" button.
  Validation evidence:
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
- **RM-SYNC-A17C — Sync Master Roadmap after A17C Hidden Guardrails** (DONE/PUSHED/REMOTE_VERIFIED) — roadmap sync gate recording commit hashes, validation evidence, and hidden UX guardrail status.
  Validation evidence:
  - commit: `6371ea7dca8a83664fceb75a622a1b2482f3f9b6`
  - git diff --check: PASS
  - post-push remote verification: PASS
- **AI-GW-A17C — Workspace Chat helper / Hidden UX Guardrails** (DONE/PUSHED/REMOTE_VERIFIED) — test-first hidden UX guardrails to prevent regression to cockpit complexity.
  Validation evidence:
  - commit: `bc45d88f18650b1bea172572d1c2cafdd1c65864 — Harden Workspace Chat hidden UX guardrails`
  - focused test: 23 passed
  - A17A/A17B regression: 61 passed
  - full pytest: 857 passed
  - diff check: PASS
  - force push used: NO
  - only test files changed
  - no normal UI changes
  - accepted caveat: a single `gate` match in comment/docstring at `workspace_chat_app.py:1020` (does not display to user).
- **RM-SYNC-UI-NOTEBOOKLM-CLEANUP — Sync Master Roadmap after Workspace Chat UI Cleanup** (DONE/PUSHED/REMOTE_VERIFIED) — roadmap sync gate recording commit hashes, validation evidence, and absolute NotebookLM-simple UX lock.
  Validation evidence:
  - commit: `007800f982a31f4caa0c0b9bc031387eb74cd2ab`
  - git diff --check: PASS
  - post-push remote verification: PASS
- **Workspace Chat NotebookLM-simple cleanup** (DONE/PUSHED/REMOTE_VERIFIED / OWNER_VISUAL_SMOKE_PASS) — simplified Workspace Chat daily UX.
  Validation evidence:
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
  - post-push remote verification: PASS
- **RM-SYNC-A17B — Sync Master Roadmap after AI-GW-A17B** (DONE/PUSHED/REMOTE_VERIFIED) — roadmap sync gate recording commit hashes, validation evidence, and absolute NotebookLM-simple UX lock.
  Validation evidence:
  - commit: `dd7394b5859c1cdda2aa1da849ec715b1fd0c9ee`
  - git diff --check: PASS
  - post-push remote verification: PASS
- **AI-GW-A17B — Result Import MVP** (DONE/PUSHED/REMOTE_VERIFIED) — parser and validation checks for agent reports.
  Validation evidence:
  - focused A17B tests: 42 passed
  - A17A + A17B regression: 61 passed
  - full pytest: 855 passed
  - git diff --check: PASS
  - uv.lock: absent / not tracked
  - source scan: PASS, only safe comment match
  - force push used: NO
  - post-push remote verification: PASS
- **AI-GW-A17A — Agent Task Pack Export MVP** (DONE/PUSHED/REMOTE_VERIFIED) — local-only task pack export with SHA-256 integrity hash, canonical JSON, task ID validation, privacy and destination checks, and atomic export.
- **AI-GW-A17-DESIGN — IDE Agent Bridge docs-only design** (DONE/PUSHED/REMOTE_VERIFIED) — architecture boundaries, result import, task pack schema and safety prompt design completed.
- **RM-SYNC-A17A — Sync Master Roadmap after AI-GW-A17A** (DONE/PUSHED/REMOTE_VERIFIED) — roadmap sync gate recording A17A hashes and backlog.
- **RM-SYNC-A16 — Sync Master Roadmap after AI-GW-A16** (DONE/PUSHED/REMOTE_VERIFIED) — roadmap naming, baseline, commit timeline, and prompt governance synchronized after A16.
- **AI-GW-A16 — Router Mock Integration with Owner Consent Gateway** (DONE/CLOSED/REMOTE_SYNCED) — mock router adapter, privacy gateway, no real provider calls, local validation tests.
- **Gate 1C — Workspace Chat Source Library / Source Management UX** (COMPLETE) — implemented search/filter, bulk actions, source toggle, and delete confirmation.
- **AI-GW-A15 — Brain Gateway Integration Design** (COMPLETE) — documented brain gateway integration design, system inventory, router adapters, IDE bridge, and import designs.

Risks & Gaps:

- local brain runtime has not been aligned or implemented.
- router mock is implemented.
- A17D is complete as a hidden Workspace Chat router adapter behind the normal Ask path; no IDE bridge UI/runtime, Router Server, dashboard, queue, or metrics UI is exposed to normal users, and the IDE bridge remains unopened. (A17C is complete as hidden UX guardrail tests).
- NotebookLM comparison arena is not yet implemented.
- Old legacy AI code is intentionally retained for reference and will be migrated/deprecated in step with the new gateway.
- Real provider API calls are strictly blocked in AI-GW-A16 (mock only).
- P1.0 remains locked.
- Accepted A17A hardening backlog:
  - A17A-HARDEN-1: `repo_path_policy` is required but not strict enum-validated. Future hardening should normalize to strict design enum such as `local_owner_only_absolute | logical_relative`.
  - A17A-HARDEN-2: `machine_only` / `cloud_safe` privacy classes are still permitted. Future hardening should normalize privacy class policy before any broader external/cloud use.
  - A17A-HARDEN-3: Recursive scanning of all structured text fields is not comprehensive. Future hardening should add deeper structured text scanning before broader external/cloud use.

---

## Historical Gate & Phase Status

- M1 to M1.8D-R: completed local-first foundation, workspace/notebook, in-app Q&A, NotebookLM bridge persistence and governance sync.

- Provider/router foundation, safety modes, one-screen daily UI, normal-provider UI pilot and company/mật privacy guard: completed with warnings.

- Search / many-case management: NOT_READY.

- P1.0: LOCKED.

---

## RAG / Document Intelligence Research-First Track

1. **Principle:**

   AIOS_habbit must not hand-write large RAG/extraction components blindly. Research strong repos/libraries first, then implement thin adapters with tests and benchmark.

2. **Scope:**

   This is not only Excel/PDF/PPTX/Image OCR. It covers:

   - extraction
   - ingestion pipeline
   - chunking
   - metadata/citation schema
   - retrieval
   - reranking
   - answer synthesis
   - evaluation
   - benchmark
   - owner workflow

3. **Reference libraries/repos to study:**
   - Docling
   - Unstructured
   - MarkItDown
   - PyMuPDF4LLM
   - MinerU / RAGFlow DeepDoc
   - LlamaIndex
   - Haystack
   - Qdrant hybrid search
   - RAGAS / DeepEval / TruLens

4. **Current status:**
   - Excel and PDF adapters added, improving AIOS RAG capability.
   - PDF text-layer ingestion added with `pymupdf4llm>=1.28.0` (FIX-MOM-PDF-INGESTION-RETRIEVAL-MIN is DONE/PUSHED/REMOTE_VERIFIED).
   - Local index smoke test successfully processed 52 files seen: 21 Excel files, 6 PDF files (42 chunks), 25 other files, yielding 518 chunks total.
   - Q1 (MES/MOM comparison) and Q2 (Production History) retrieval improved via CJK tokenization and domain-tuned boosters.
   - Q3 Excel retrieval preserved with no regression.
   - Image OCR, PPTX OCR, and richer HTML/DOCX/log parsing remain future tracks.
   - NotebookLM parity is not claimed.
   - P1.0 is not opened.
   - Remaining caveats: Q3 Excel answer composer is still pending; router-grounded MOM answer path is deferred; PNG OCR remains deferred/no local OCR in this MVP.

5. **Priority:**
   - Completed local-first PDF ingestion and search ranking improvements.
   - Excel and PDF local index and retrieval gaps are minimized.
   - Rerun NotebookLM battle is pending to verify answers using the official local AIOS index.
   - Do not add Vector DB/Graph DB until extraction and benchmark prove need.

6. **Governance:**
   - No fake parity.
   - No real docs/runtime outputs committed.
   - No vector/graph drift.
   - Owner acceptance still required.

## M1.10 - Antigravity Bridge Manual-Step Reduction

Exit criteria:

- Owner can create a local Antigravity handoff bundle from Case Cockpit.
- Owner can import a response from the UI without CLI.
- Raw JSON paste is not required as the default path.
- Privacy and citation validation are enforced.
- Validated answer is saved back to the case.
- Bridge tests and full pytest pass.

## M1.11 - Visual Knowledge Map MVP Design

Status: DESIGN_READY.

Scope:

- Design a local-first evidence-grounded work graph for Cases, Evidence, Sources, Claims, Answers, Decisions, Actions, Risks, Learning Cards, and Domain Playbooks.
- Define generic node and typed edge schemas.
- Define deterministic graph generation pipeline, privacy export modes, UI MVP boundaries, and future tests.
- Keep the graph generic across HR, accounting, Japanese learning, IT manuals, legal/contracts, manufacturing, and general office work.

Not included:

- No graph UI implementation yet.
- No new visualization library yet.
- No NotebookLM replacement or parity claim.
- No P1.0 opening.

## Program Progress Estimate & Metrics

- **AI Brain Gateway architecture:** design done, runtime readiness increased from 25-30% to 35-40% (A16 mock router guard is completed).
- **Router integration (real):** 10-15% (mock-only).
- **IDE Agent Bridge:** design complete, runtime implementation not started (5%).
- **NotebookLM Comparison Arena:** 0-5%.
- **Overall Program Progress:** estimated at 38-42% (qualitative estimate).

## Prompt & Gate Governance

- Every future AIOS_habbit agent prompt must reference the master roadmap.
- If a task changes phase, gate name, scope, status, commit timeline, next gate, or P1.0 lock condition, the task must include a roadmap sync requirement.
- Do not open a new implementation gate when the roadmap is stale.
- Do not call a gate DONE unless it has PASS evidence, commit status, push status, and remote verification when required.

## Gate Family Naming Standard

- WSC-* = Workspace Chat Foundation gates.
- AI-GW-* = AI Brain Gateway / Router / Agent gates.
- RM-SYNC-* = Roadmap synchronization gates.

## Commit Timeline Policy

- Functional gate commits and major roadmap sync commits may be recorded as historical evidence.
- The current repository HEAD is not maintained inside this roadmap to avoid self-referential stale hashes.
- To verify current HEAD/origin, run `git rev-parse HEAD` and `git rev-parse origin/main` during the active gate.

## Commit Timeline

- **12. AI-GW-A16 Router Mock Integration:** `5cf0cca9cdc9f5b4b2a22a45e0525cb4d8c050d4` — Message: Add AIOS brain gateway mock router guard
- **13. RM-SYNC-A16 Roadmap Sync after AI-GW-A16:** `bf4c39c9b6b44611b826be3201bbdf39e8cae099` — Message: Sync roadmap after AI-GW-A16
- **14. RM-SYNC-A16 Stale Status Fix:** `f3a9b6c42d2aa40f2cd225f1684d70c06e9dc039` — Message: Fix roadmap sync status after A16
- **15. AI-GW-A17-DESIGN IDE Agent Bridge Design:** `6ea3f573e62db7fbb4bf2089e0f6f2eb932394e5` — Message: Unify A17 design destination enum
- **16. AI-GW-A17A Agent Task Pack Export MVP:** `a2660583c53d2eb67c6123a36648fbc74d4b8879` — Message: Add A17A agent task pack export MVP
- **17. AI-GW-A17A Blockers Fix:** `3da1882f8d7c71968d35cea15078d43dc9d8bcce` — Message: Fix A17A task pack export audit blockers
- **18. RM-SYNC-A17A Roadmap Sync after AI-GW-A17A:** `bb154657a6843724f4eb201f197f43acf3e68d2a` — Message: Sync roadmap after A17A task pack export
- **19. AI-GW-A17B Agent Result Import MVP:** `65449764d7a35b0ace01891e8e02028f9db9eef2` — Message: Add A17B agent result import MVP
- **20. AI-GW-A17B Audit Blockers Fix:** `75a8f0be64586df0cedfb6ddfc28c0f32225d82a` — Message: Fix A17B result import audit blockers
- **21. RM-SYNC-A17B Roadmap Sync after AI-GW-A17B:** `dd7394b5859c1cdda2aa1da849ec715b1fd0c9ee` — Message: Sync A17B roadmap and NotebookLM-simple UX lock
- **22. Workspace Chat NotebookLM-simple UI Cleanup:** `f23ea1345e1c3644f6037aa21ee428077cf1ac5a` — Message: Simplify Workspace Chat daily UX
- **23. AI-GW-A17C Workspace Chat Hidden UX Guardrails:** `bc45d88f18650b1bea172572d1c2cafdd1c65864` — Message: Harden Workspace Chat hidden UX guardrails
- **24. RM-SYNC-A17C Roadmap Sync after AI-GW-A17C:** `6371ea7dca8a83664fceb75a622a1b2482f3f9b6` — Message: Sync A17C hidden guardrail status
- **25. AI-GW-A17D Hidden Router Adapter for Workspace Chat Ask:** `0c79958805faf1b45d3df53976a832dde1109bd7` — Message: Add hidden router adapter for Workspace Chat ask
- **26. RM-SYNC-A17D Roadmap Sync after AI-GW-A17D:** `eb97f44216eddd56939a4a3f86ded672aa4b3083` — Message: Sync A17D hidden router status
- **27. FIX-MOM-PDF-INGESTION-RETRIEVAL-MIN MOM PDF Ingestion and Retrieval Ranking:** `361bbc470db4970e584991b029c06f2f8846e910` — Message: Improve MOM PDF ingestion and retrieval ranking
