# AIOS WorkLens High-Level Roadmap Index

AIOS WorkLens / AIOS_habbit là một **hệ điều hành trí nhớ công việc cá nhân, local-first**: biến tài liệu, Excel, ảnh, log, chat, email, AI output và sự việc hằng ngày thành tri thức tái sử dụng theo vòng:

```text
Case → Evidence → Map → Action → Learning → Memory
```

## Core Reference Documents

- **Product North Star & Doctrine:** [PRODUCT_NORTH_STAR.md](file:///D:/Sandbox/AIOS_habbit/PRODUCT_NORTH_STAR.md)
- **Master Roadmap & Governance:** [WORKLENS_MASTER_ROADMAP.md](file:///D:/Sandbox/AIOS_habbit/WORKLENS_MASTER_ROADMAP.md)
- **Product Positioning:** [docs/AIOS_PRODUCT_POSITIONING.md](file:///D:/Sandbox/AIOS_habbit/docs/AIOS_PRODUCT_POSITIONING.md)

---

## Active Position

- **Local HEAD:** `f28663b` (`Document roadmap review after normal provider UI pilot`).
- **Remote HEAD:** `214c44f` (`Clarify provider fallback reason in daily flow`).
- **Current position:** End of Phase 3, before Phase 4 RAG Engine v2 and Phase 5 IDE/model bridge.
- **Current capability:** daily-pilot ready for normal documents, not production-ready.
- **P1.0:** LOCKED; do not open until readiness criteria are met.
- **NotebookLM parity:** NOT achieved; current retrieval is useful but not NotebookLM-level.
- **IDE/model bridge:** NOT implemented yet.

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

---

## Next Gate Queue

Immediate:
1. **AIOS-RAG-AGENT-HARNESS-0** — research RAG + Claude-Code-style harness patterns, docs only.
2. **AIOS-RAG-INGEST-1** — improve parser/chunk metadata, no vector DB yet.
3. **AIOS-RAG-SEARCH-1** — local hybrid search foundation, SQLite FTS/BM25, metadata filters, citation IDs.
4. **AIOS-RAG-EVIDENCE-PACK-1** — evidence pack builder, source scoring, answer abstention.
5. **AIOS-IDE-BRIDGE-1** — manual prompt export, paste-back answer, store model/tool/evidence/route log.

Later:
6. AIOS-RAG-RERANK-1
7. AIOS-RAG-BENCHMARK-1
8. AIOS-CASE-SCALE-1
9. AIOS-WORKSTREAM-MAP-1
10. AIOS-P1-READINESS-CHECKLIST

---

## Historical Gate & Phase Status

- M1 to M1.8D-R: completed local-first foundation, workspace/notebook, in-app Q&A, NotebookLM bridge persistence and governance sync.
- Provider/router foundation, safety modes, one-screen daily UI, normal-provider UI pilot and company/mật privacy guard: completed with warnings.
- Search / many-case management: NOT_READY.
- P1.0: LOCKED.
