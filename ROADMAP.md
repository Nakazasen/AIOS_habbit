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



## Active Position

- **Local HEAD:** `8adab34` (`Mark Workspace Chat as primary UI`).
- **Remote HEAD:** `8adab34` (`Mark Workspace Chat as primary UI`).
- **Current position:** Workspace Chat is the primary UI; local retrieval, multi-file uploader, and Vietnamese encoding are fully implemented and pushed.
- **Current capability:** Workspace Chat supports notebook lifecycle, hard delete, multi-format sources, local retrieval, and image/WebP OCR.
- **P1.0:** LOCKED; remains locked until the Gate 1C Source Library UX is stable.
- **NotebookLM parity:** NOT achieved; retrieval and source library still require MVP improvements before parity claims.
- **IDE/model bridge:** Manual IDE response import and full-bundle outbox/inbox is fully operational.





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



### Phase 4 — RAG Engine v2 / NotebookLM-level Retrieval



Status: IN PROGRESS.



Scope:

- Ingest: `RAGChunk` and `RAGDocumentElement` with stable IDs (DONE `AIOS-RAG-INGEST-1`).

- Search: Local SQLite FTS/BM25 + fallback string search (DONE `AIOS-RAG-SEARCH-1`).

- Pack: Evidence pack builder, source scoring, and answer abstention (DONE `AIOS-RAG-EVIDENCE-PACK-1`).

- Rerank: Local semantic reranker (PENDING `AIOS-RAG-RERANK-1`).

- cloud embedding for company/mật;

- fake NotebookLM parity claim.



### Phase 5 — IDE / Strong Model Answer Bridge



Status: DONE.



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

0. **Gate 1C — Workspace Chat Source Library / Source Management UX** - IN PROGRESS; implement search/filter, bulk toggle, temporary source deletion, and failed upload visibility in Workspace Chat.

1. **AIOS-RAG-EVIDENCE-PACK-1** — evidence pack builder, source scoring, answer abstention.

2. **AIOS-RAG-INGEST-1** — improve parser/chunk metadata, no vector DB yet.

3. **AIOS-RAG-SEARCH-1** — local hybrid search foundation, SQLite FTS/BM25, metadata filters, citation IDs.

4. **AIOS-IDE-BRIDGE-1** — manual prompt export, paste-back answer, store model/tool/evidence/route log.

5. **Visual Map MVP** — DONE; local JSON/Mermaid export, schema models, deterministic active-case graph builder, UI stub.



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
   - Excel adapter added and improved AIOS RAG.
   - AIOS insufficient evidence dropped from 12/12 to 2/12 after Excel extraction + FTS Unicode/search fixes.
   - PDF, PPTX, image/OCR, richer HTML/DOCX/log parsing remain future adapter tracks.
   - NotebookLM parity is not claimed.
   - P1.0 is not opened.

5. **Priority:**
   - First, finish fair comparison after Excel extraction.
   - Then choose next adapter by evidence.
   - Likely next adapter: PDF via PyMuPDF4LLM, but only after comparison report.
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
