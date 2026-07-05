# WorkLens Master Roadmap & Governance

Every phase of the AIOS WorkLens lifecycle must use strict PASS/FAIL gates. A phase or gate is not considered complete until deliverables, validation evidence, handover, privacy impact, and rollback options are clearly documented.

AIOS WorkLens is a local-first personal work memory operating system. The core loop is:

```text
Case → Evidence → Map → Action → Learning → Memory
```

---

## 1. Current Gate Status

### Repository State Policy

- Authoritative current HEAD/origin state must be verified by Git during each gate.
- This roadmap intentionally does not claim the hash of its own latest commit.
- Commit hashes recorded below are historical gate evidence, not self-updating current HEAD fields.

### Active Position

- Current phase: Phase 4 — Workspace Chat Foundation & AI Gateway Preparation.
- Latest closed implementation gate: AI-GW-A16 — Router Mock Integration with Owner Consent Gateway — DONE/CLOSED/REMOTE_SYNCED.
- Latest roadmap sync gate: RM-SYNC-A16 — Sync Master Roadmap after AI-GW-A16 — DONE/PUSHED; remote verification is handled by external audit/post-push records, not self-attested by this file.
- Next candidate gate: AI-GW-A17 — IDE Agent Bridge — NOT_STARTED / NEXT_CANDIDATE; planning/design only, implementation not opened.
- AI-GW-A18 — NotebookLM Comparison Arena — NOT_STARTED.
- P1.0 — Owner Pilot / Productization — LOCKED.

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

### Phase 4 — Workspace Chat Foundation & AI Gateway Preparation

Status: IN PROGRESS.

*Note: M1.x is an internal milestone stream under Phase 4, not a separate product phase.*

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

Status: DONE_WITH_WARNINGS / FOUNDATION_DONE.

Clarification:

- Manual IDE answer/evidence bridge foundation exists: prompt/evidence pack export, paste-back answer import, model/tool name, evidence refs, route summary, and privacy guard.
- AI-GW-A17 repo-task pack / trusted result-import bridge is NOT_STARTED / NEXT_CANDIDATE.
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

- **AI-GW-A17 — IDE Agent Bridge** (NOT_STARTED / NEXT_CANDIDATE) — planning/design gate only; implementation not opened yet.
- **AI-GW-A18 — NotebookLM Comparison Arena** (NOT_STARTED) — after A17 or later strategy decision.

Completed:

- **RM-SYNC-A16 — Sync Master Roadmap after AI-GW-A16** (DONE/PUSHED/REMOTE_VERIFIED) — roadmap naming, baseline, commit timeline, and prompt governance synchronized after A16.
- **AI-GW-A16 — Router Mock Integration with Owner Consent Gateway** (DONE/CLOSED/REMOTE_SYNCED) — mock router adapter, privacy gateway, no real provider calls, local validation tests.
- **Gate 1C — Workspace Chat Source Library / Source Management UX** (COMPLETE) — implemented search/filter, bulk actions, source toggle, and delete confirmation.
- **AI-GW-A15 — Brain Gateway Integration Design** (COMPLETE) — documented brain gateway integration design, system inventory, router adapters, IDE bridge, and import designs.

Risks & Gaps:

- local brain runtime has not been aligned or implemented.
- router mock is implemented.
- IDE bridge runtime is not yet implemented.
- NotebookLM comparison arena is not yet implemented.
- Old legacy AI code is intentionally retained for reference and will be migrated/deprecated in step with the new gateway.
- Real provider API calls are strictly blocked in AI-GW-A16 (mock only).
- P1.0 remains locked.

---

## 5. Model Role Rules

- **Audit Specialist:** independent audits, code reviews, anti-fake PASS checks, validation confirmation.
- **Execution Specialist:** coding and test execution only after an approved plan.
- **Strict Constraint:** no feature merge is allowed without audit review and validation confirmation.

---

## 6. Legacy Repository Policy

The repository `AIOS_habbit` is the central repository for WorkLens. Legacy repositories are read-only references only. Do not copy code blocks directly, do not use leaked/proprietary code, and do not harvest ingest/graph/agent bridge code before an approved audit gate.

---

## 7. Program Progress Estimate & Metrics

- **AI Brain Gateway architecture:** design done, runtime runtime increased from 25-30% to 35-40% (A16 mock router guard is completed).
- **Router integration (real):** 10-15% (mock-only).
- **IDE Agent Bridge runtime:** 5%.
- **NotebookLM Comparison Arena:** 0-5%.
- **Overall Program Progress:** estimated at 38-42% (qualitative estimate).

## 8. Prompt & Gate Governance

- Every future AIOS_habbit agent prompt must reference the master roadmap.
- If a task changes phase, gate name, scope, status, commit timeline, next gate, or P1.0 lock condition, the task must include a roadmap sync requirement.
- Do not open a new implementation gate when the roadmap is stale.
- Do not call a gate DONE unless it has PASS evidence, commit status, push status, and remote verification when required.

## 9. Commit Timeline

### Commit Timeline Policy

- Functional gate commits and major roadmap sync commits may be recorded as historical evidence.
- The current repository HEAD is not maintained inside this roadmap to avoid self-referential stale hashes.
- To verify current HEAD/origin, run `git rev-parse HEAD` and `git rev-parse origin/main` during the active gate.

### Historical Commits

- **12. AI-GW-A16 Router Mock Integration:** `5cf0cca9cdc9f5b4b2a22a45e0525cb4d8c050d4` — Message: Add AIOS brain gateway mock router guard
- **13. RM-SYNC-A16 Roadmap Sync after AI-GW-A16:** `bf4c39c9b6b44611b826be3201bbdf39e8cae099` — Message: Sync roadmap after AI-GW-A16
- **14. RM-SYNC-A16 Stale Status Fix:** `f3a9b6c42d2aa40f2cd225f1684d70c06e9dc039` — Message: Fix roadmap sync status after A16

---

## 10. Gate Family Naming Standard

- WSC-* = Workspace Chat Foundation gates.
- AI-GW-* = AI Brain Gateway / Router / Agent gates.
- RM-SYNC-* = Roadmap synchronization gates.
