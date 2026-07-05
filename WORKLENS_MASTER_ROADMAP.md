# WorkLens Master Roadmap & Governance

Every phase of the AIOS WorkLens lifecycle must use strict PASS/FAIL gates. A phase or gate is not considered complete until deliverables, validation evidence, handover, privacy impact, and rollback options are clearly documented.

AIOS WorkLens is a local-first personal work memory operating system. The core loop is:

```text
Case → Evidence → Map → Action → Learning → Memory
```

---

## 1. Current Gate Status

- **Current local HEAD:** `44d40f4` (`Document AIOS brain gateway integration design`).
- **Current remote HEAD:** `44d40f4` (`Document AIOS brain gateway integration design`).
- **Current position:** Brain Gateway integration design is completed; Workspace Chat is the primary UI, and Source Library Management (WSC-1C) is fully implemented and pushed.
- **P1.0:** LOCKED. Do not open automatically; remains locked until the router mock/privacy gateway and owner-facing AI flow are safe and stable.
- **NotebookLM parity:** not achieved; Retrieval Engine v2 and Source Library MVP are required.
- **IDE/model bridge:** Manual IDE response import is operational; Brain Gateway integration design is ready for router mock implementation.

Completed foundation gates include local Case Cockpit, Workspace/Knowledge Notebook, MOM local benchmark, provider safety modes, route log, one-screen daily UI, DeepSeek normal-document UI pilot, Q&A-to-Case route summary, company/mật privacy guard, Workspace Chat primary UI, multi-format uploader, local retrieval/evidence items, Vietnamese mojibake cleanup, legacy retirement docs sync, Workspace Chat Source Library (WSC-1C), and Brain Gateway integration design (AI-GW-A15).

---

## 2. Phase Roadmap

### Phase 0 — Vision & Governance

Status: DONE.

Scope: mission, local-first rules, no fake PASS, privacy constraints, roadmap guardrails.

### Phase 1 — Local Case Cockpit Foundation

Status: DONE.

Scope: case model, evidence, quick intake, handoff, learning card, audit gates.

### Phase 2 — Real Document / MOM Foundation

Status: DONE_WITH_WARNINGS.

Scope: MOM local ingest/index, 50Q benchmark, source refs, local-only guard, NotebookLM comparison baseline.

Warning: not NotebookLM-level semantic retrieval yet.

### Phase 3 — Provider Safety + Daily UI

Status: DONE_WITH_WARNINGS.

Scope: Vietnamese safety modes, provider catalog, route log, DeepSeek normal-doc UI pilot, one-screen daily flow, Q&A to Case route summary.

Warning: daily-pilot ready, not production-ready.

### Phase 4 — RAG Engine v2 / NotebookLM-level Retrieval

Status: NEXT.

Scope:
- better parser adapter;
- structure-aware chunks;
- SQLite FTS / BM25;
- optional embeddings later;
- hybrid search;
- rerank;
- query rewrite;
- evidence pack;
- citation scoring;
- NotebookLM-style benchmark.

Not allowed yet:
- heavy vector DB without decision;
- cloud embedding for company/mật;
- fake NotebookLM parity claim.

### Phase 5 — IDE / Strong Model Answer Bridge

Status: NEXT_PARALLEL.

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

Scope: many-case search, case index, duplicate detection, cross-case lessons, timeline, tags/entities, find similar incident.

Warning: currently NOT_READY.

### Phase 7 — Work Stream Map / Knowledge Graph

Status: LATER.

Scope: work stream graph, case/evidence/action relation, lightweight graph first, no graph DB until proven necessary.

### Phase 8 — Senior Learning / Personal OS

Status: LATER.

Scope: senior learning memory, repeated workflow extraction, communication style, decision pattern, reusable prompts, AI-independent personal memory.

### Phase 9 — Production Traceability Foundation

Status: LATER.

Scope: generic unit traceability foundation, not LSU-only, LSU/Drum/DLP/Fuser/Scanner/MainBody/Other, fake CSV first, simple join/risk summary.

Forbidden: prediction engine, ML, production DB integration, long research branch.

### Phase 10 — P1.0 Production Readiness

Status: LOCKED.

Open only if owner completes a real daily scenario without agent assistance, RAG v2 benchmark passes, privacy audit passes, route log/case/evidence trace is stable, docs/user guide are ready, and no secret/runtime commit risk remains.

---

## 3. Why model call is only a small part

AIOS quality depends on parser, index, retrieval, rerank, evidence pack, context, model, privacy guard and route log. Stronger models are useful but cannot compensate for weak evidence selection or unsafe privacy routing. Free/low-tier models are not enough for complex company documents. Strong models should be used through a safe IDE/model bridge that exports evidence packs and stores paste-back answers with model/tool name, evidence refs, route summary and privacy mode.

Learning sources for public pattern research: RAGFlow, kotaemon, Microsoft GraphRAG, LightRAG, LlamaIndex, Haystack, Docling, Unstructured, OpenHands, Aider, Cline, Continue, Goose, Cognee, Letta/MemGPT, LangGraph, Semantic Kernel. Do not copy leaked/proprietary code.

---

## 4. Next Gate Queue

Immediate:
- **AI-GW-A16 — Router Mock Integration** (IN PROGRESS) — mock router adapter, privacy gateway, no real provider calls, local validation tests.
- **AI-GW-A17 — IDE Agent Bridge** (PENDING) — runtime integration for agent workspace and IDE messaging bridge.
- **AI-GW-A18 — NotebookLM Comparison Arena** (PENDING) — comparative evaluation between local RAG and NotebookLM.

Completed:
- **Gate 1C — Workspace Chat Source Library / Source Management UX** (COMPLETE) — implemented search/filter, bulk actions, source toggle, and delete confirmation.
- **AI-GW-A15 — Brain Gateway Integration Design** (COMPLETE) — documented brain gateway integration design, system inventory, router adapters, IDE bridge, and import designs.

Risks & Gaps:
- local brain runtime has not been aligned or implemented.
- router mock is not yet implemented.
- IDE bridge runtime is not yet implemented.
- NotebookLM comparison arena is not yet implemented.
- Old legacy AI code is intentionally retained for reference and will be migrated/deprecated in step with the new gateway.
- Real provider API calls are strictly blocked in AI-GW-A16 (mock only).
- Roadmap drift fixed for A15.

---

## 5. Model Role Rules

- **Audit Specialist:** independent audits, code reviews, anti-fake PASS checks, validation confirmation.
- **Execution Specialist:** coding and test execution only after an approved plan.
- **Strict Constraint:** no feature merge is allowed without audit review and validation confirmation.

---

## 6. Legacy Repository Policy

The repository `AIOS_habbit` is the central repository for WorkLens. Legacy repositories are read-only references only. Do not copy code blocks directly, do not use leaked/proprietary code, and do not harvest ingest/graph/agent bridge code before an approved audit gate.
