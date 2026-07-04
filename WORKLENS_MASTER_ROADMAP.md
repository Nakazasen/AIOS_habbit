# WorkLens Master Roadmap & Governance

Every phase of the AIOS WorkLens lifecycle must use strict PASS/FAIL gates. A phase or gate is not considered complete until deliverables, validation evidence, handover, privacy impact, and rollback options are clearly documented.

AIOS WorkLens is a local-first personal work memory operating system. The core loop is:

```text
Case → Evidence → Map → Action → Learning → Memory
```

---

## 1. Current Gate Status

- **Current local HEAD:** `8adab34` (`Mark Workspace Chat as primary UI`).
- **Current remote HEAD:** `8adab34` (`Mark Workspace Chat as primary UI`).
- **Current position:** Workspace Chat is established as the primary UI; legacy Studio and Case Cockpit are retained as reference/debug only.
- **P1.0:** LOCKED. Do not open automatically.
- **NotebookLM parity:** not achieved; Retrieval Engine v2 and Source Library MVP are required.
- **IDE/model bridge:** Manual IDE response import is operational; direct cloud calls remain blocked for local-only evidence.

Completed foundation gates include local Case Cockpit, Workspace/Knowledge Notebook, MOM local benchmark, provider safety modes, route log, one-screen daily UI, DeepSeek normal-document UI pilot, Q&A-to-Case route summary, company/mật privacy guard, Workspace Chat primary UI, multi-format uploader, local retrieval/evidence items, Vietnamese mojibake cleanup, and legacy retirement docs sync.

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
1. **Gate 1C — Workspace Chat Source Library / Source Management UX** — IN PROGRESS; implement search/filter, bulk actions, temporary source cleanup with warnings, and failed upload visibility in Workspace Chat.
2. **AIOS-RAG-EVIDENCE-PACK-1** — evidence pack builder, source scoring, answer abstention.
3. **AIOS-RAG-INGEST-1** — improve parser/chunk metadata, no vector DB yet.
4. **AIOS-RAG-SEARCH-1** — local hybrid search foundation, SQLite FTS/BM25, metadata filters, citation IDs.
5. **AIOS-IDE-BRIDGE-1** — manual prompt export, paste-back answer, store model/tool/evidence/route log.

Later:
6. AIOS-RAG-RERANK-1
7. AIOS-RAG-BENCHMARK-1
8. AIOS-CASE-SCALE-1
9. AIOS-WORKSTREAM-MAP-1
10. AIOS-P1-READINESS-CHECKLIST

---

## 5. Model Role Rules

- **Audit Specialist:** independent audits, code reviews, anti-fake PASS checks, validation confirmation.
- **Execution Specialist:** coding and test execution only after an approved plan.
- **Strict Constraint:** no feature merge is allowed without audit review and validation confirmation.

---

## 6. Legacy Repository Policy

The repository `AIOS_habbit` is the central repository for WorkLens. Legacy repositories are read-only references only. Do not copy code blocks directly, do not use leaked/proprietary code, and do not harvest ingest/graph/agent bridge code before an approved audit gate.
