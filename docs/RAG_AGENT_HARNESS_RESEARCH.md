# RAG Agent Harness Research

Gate: AIOS-RAG-AGENT-HARNESS-0  
Status: research/design only  
Date: 2026-06-28

## Executive Summary

AIOS should evolve from the current useful local notebook/Q&A flow into a local-first work memory RAG system. The next architecture should not start with a heavy vector database or graph database. It should first strengthen document parsing, chunk metadata, local hybrid retrieval, evidence packing, citations, privacy gating, and benchmark discipline.

The main lesson from public RAG systems is that strong answers come from the full chain: parser, layout/table/OCR preservation, chunk identity, hybrid search, rerank, evidence packs, context compression, answer abstention, and audit logs. The model call is only one step.

The main lesson from agent/IDE tools is that AIOS should begin with safe prompt export and paste-back answer storage. Tool/IDE automation can come later behind permission gates, explicit approval, audit logs, and rollback.

## Current AIOS Retrieval and Harness Audit

### Ingest

Current implementation includes local document extraction helpers in `src/aios_habit/document_extractors.py` and notebook source/index flows in `source_ingest.py`, `notebook_index.py`, and MOM-specific local index code.

Current strengths:
- Supports text/markdown-style source content in notebook index.
- Document extractor has local handlers for HTML, PPTX, Excel via `openpyxl`, images, OCR-limited PDFs/images via local Tesseract where available, and ZIP/XML-based parsing for Office documents.
- Chunk metadata already includes source file, relative path, file type, section, page, slide, sheet, row range, privacy level, extractor name, extraction status, OCR engine, and OCR language.
- Privacy defaults are local-first for extracted chunks.

Limitations:
- Notebook index currently uses fixed character chunks and simple keyword extraction.
- Document structure is not yet normalized into one stable cross-format chunk schema for all downstream QA paths.
- Excel handling is preview-limited and not yet robust for multi-sheet table retrieval.
- OCR is intentionally bounded and local-only but not a high-fidelity scanned document pipeline.
- Image/figure semantics are not yet understood beyond OCR/media markers.
- Not NotebookLM-level layout-aware retrieval yet.

### Retrieval

Current strengths:
- `notebook_index.py` provides local chunk loading/building and keyword search.
- Ranking combines exact phrase, title, filename, and token frequency scores.
- MOM benchmark/index modules exist for local-only document evaluation.

Limitations:
- No SQLite FTS/BM25 foundation yet.
- No vector index yet.
- No hybrid ranking, reranking, query rewrite, synonym expansion, or multilingual query planning.
- Limited metadata filtering and no evidence diversity controls.
- Citation labels are source/chunk based but not yet stable enough for NotebookLM-style source-grounded answer verification.
- Many-document/many-case search is marked NOT_READY.

### Answer

Current strengths:
- Local deterministic fallback exists.
- Provider route answer exists through `ai_router.py` and `ai_provider_bridge.py` for normal documents.
- Route log includes provider/model/attempt status and whether content was sent outside.
- Q&A to Case flow preserves route summary and evidence references.
- Privacy handling blocks company/mật content from cloud routes.

Limitations:
- Evidence packs are implicit; there is no first-class evidence pack object with coverage/confidence/abstention metadata.
- Answer composer does not yet separate known facts, inference, missing evidence, and recommended next evidence.
- Citation scoring is not yet explicit.

### Agent / Model Bridge

Current strengths:
- Provider catalog and router exist for controlled normal-document provider use.
- Route summary and provider attempts are tracked.
- Export pack directories exist as ignored runtime artifacts, but no committed IDE bridge implementation exists.

Missing:
- No prompt pack ID model.
- No committed manual prompt export workflow.
- No paste-back answer model with model/tool name, prompt ID, evidence refs, route summary, confidence, and warnings.
- No tool/IDE adapter layer.
- No agent harness with task state, permissions, context compaction, subtask delegation, rollback, or handoff.

Why free/low-tier model is not enough:
- Complex work documents fail when parser, chunking, retrieval, or evidence selection are weak.
- Free/low-tier models are useful for low-risk public notes but cannot guarantee grounded analysis of tables, scans, multi-hop cases, or company/mật workflows.
- Strong models should be used through evidence-grounded, privacy-aware prompt packs, not raw document uploads.

## External Repo / Pattern Matrix

| Target | Purpose | Useful AIOS Ideas | Do Not Copy | Difficulty | Privacy Risk | Local-first Fit | Value |
|---|---|---|---|---|---|---|---|
| RAGFlow | Deep document RAG with parsing, hybrid search, rerank, citations | Layout/table/OCR-first parsing, hybrid search, rerank, traceable citations | Do not copy source or deploy heavy stack blindly | HIGH | MEDIUM | MEDIUM | HIGH |
| kotaemon | Local/private document QA UI/framework | Local deployment, hybrid retrieval, PDF citation UX, modular components | Do not copy UI or provider configs | MEDIUM | MEDIUM | HIGH | HIGH |
| Microsoft GraphRAG | Graph-based global/local corpus reasoning | Community summaries, global vs local search, graph as later layer | Do not introduce graph DB now | HIGH | HIGH if LLM indexing is cloud | MEDIUM | MEDIUM-HIGH later |
| LightRAG | Lightweight graph + vector retrieval | Dual-layer idea, entity relation retrieval | Do not add graph/vector before local FTS gate | MEDIUM | MEDIUM | MEDIUM | MEDIUM |
| LlamaIndex | RAG/agent workflow framework | Query planning, retrievers, memory abstractions, workflows | Do not import broad framework without need | MEDIUM | MEDIUM | MEDIUM | HIGH as design reference |
| Haystack | Production RAG pipeline components | Pipeline/component boundaries, evaluation discipline | Do not over-engineer early | MEDIUM | MEDIUM | HIGH with local components | HIGH |
| Docling | Document conversion with layout/table/OCR | Unified document representation, layout/table/OCR pipeline | Do not add cloud OCR or heavy models by default | MEDIUM | LOW if local | HIGH | HIGH |
| Unstructured | Data ingestion/partitioning pipeline | Partitioning into typed elements, metadata-rich chunks | Do not send sensitive docs to cloud services | MEDIUM | MEDIUM | HIGH if local | HIGH |
| OpenHands | Autonomous coding agent platform | Isolated runtime, task logs, tool execution boundaries | Do not allow autonomous writes | HIGH | HIGH | MEDIUM | MEDIUM |
| Aider | Git-native terminal pair programmer | Git-aware change loop, diff/commit discipline | Do not auto-commit user work without gate | LOW-MEDIUM | MEDIUM | HIGH | MEDIUM |
| Cline | IDE agent with Plan/Act and permissions | Explicit approval for file edits, commands, browser actions | Do not bypass human approval | MEDIUM | MEDIUM-HIGH | HIGH | HIGH |
| Continue | IDE-native assistant framework | Context providers, model routing, IDE integration | Do not leak sensitive files into context | MEDIUM | MEDIUM | HIGH | MEDIUM-HIGH |
| Goose | Editor-agnostic agent | Task delegation, tool abstraction | Do not grant broad tool access | MEDIUM | HIGH | MEDIUM | MEDIUM |
| OpenCode | Terminal/IDE coding agent patterns | CLI workflow and tool boundaries if relevant | Do not couple AIOS to one tool | MEDIUM | MEDIUM | MEDIUM | LOW-MEDIUM |
| LangGraph | Stateful multi-actor agent graph | State machine, checkpointing, human approval nodes | Do not add complex graph runtime yet | MEDIUM | MEDIUM | HIGH if local | HIGH as design reference |
| Semantic Kernel | Plugins, memory, planner abstractions | Plugin contracts and skills/tools boundary | Do not create cloud plugin path for company/mật | MEDIUM | MEDIUM | MEDIUM | MEDIUM |
| Cognee | Memory-first graph/RAG | Cognify pipeline, graph memory ideas | Do not add graph DB before evidence need | HIGH | MEDIUM | MEDIUM | MEDIUM later |
| Letta/MemGPT | Agent memory OS | Memory tiers and self-editing memory concepts | Do not let agents silently edit memory | HIGH | HIGH | MEDIUM | HIGH conceptually |

## AIOS Retrieval Engine v2 Architecture

### 1. Document Parser Adapter

Goal: convert inputs into typed local elements while preserving structure.

Requirements:
- page, section, heading, paragraph, table, sheet, cell, slide, image, and OCR markers;
- stable document ID and source path;
- extractor status and warning fields;
- local-only default for company/mật;
- no cloud OCR unless explicitly approved and non-sensitive.

Recommended first step: adapt current `document_extractors.py` output into a normalized element schema without replacing the extractor stack.

### 2. Chunk & Metadata Builder

Required metadata:
- stable chunk ID;
- source document ID;
- source title and relative path;
- page/sheet/section/slide/table/cell range;
- text/table/image/OCR flags;
- privacy mode;
- created time;
- source hash/checksum;
- citation label;
- extractor and status;
- parent/neighbor chunk IDs for section expansion.

### 3. Local Hybrid Index

Phase 4 should start with SQLite FTS/BM25 and metadata tables.

Initial design:
- `documents` table;
- `chunks` table;
- `chunk_fts` virtual table;
- `chunk_metadata` or JSON column;
- local rebuild and incremental update by source hash;
- no cloud embedding for company/mật.

Optional vector search should come later only after FTS/BM25 benchmark gaps are measured.

### 4. Query Planner

Responsibilities:
- normalize Vietnamese/Japanese/English terms;
- expand domain synonyms for MOM/WMS/Opcenter/InterStock;
- generate multiple query variants;
- decide if question is lookup, comparison, process, root-cause, summary, or missing-evidence query;
- select metadata filters and candidate limits.

### 5. Retriever + Reranker

Initial retrieval:
- FTS/BM25 candidate search;
- filename/title/source boosts;
- metadata filters;
- exact identifier boost;
- section expansion;
- duplicate removal;
- diversity across documents/pages/sheets.

Later rerank:
- local cross-encoder or lightweight heuristic reranker first;
- optional provider rerank only for non-sensitive documents and explicit approval.

### 6. Evidence Pack Builder

Evidence pack fields:
- pack ID;
- query;
- top evidence snippets;
- citation IDs;
- source refs;
- score details;
- coverage summary;
- missing evidence warnings;
- insufficient evidence flag;
- privacy mode;
- allowed answer route.

This pack becomes the input to local answer, provider answer, prompt export, and Q&A-to-Case.

### 7. Answer Composer

Answer format:
- direct answer;
- evidence-backed facts;
- inference/hypothesis clearly labeled;
- citations per claim;
- missing evidence / cannot answer section;
- route log provider/model;
- attach-to-case summary.

Rules:
- abstain if evidence is insufficient;
- never claim NotebookLM parity until benchmark passes;
- never send company/mật evidence outside.

### 8. Benchmark Harness

Benchmark tiers:
- 20-question smoke;
- 50-question gate;
- 100-question regression.

Metrics:
- correctness;
- citation accuracy;
- hallucination rate;
- coverage;
- insufficiency detection;
- privacy behavior;
- latency;
- answer usefulness.

Comparison:
- AIOS vs NotebookLM on the same public/non-sensitive docs/questions only;
- no fake parity claim.

## AIOS IDE Answer Bridge Architecture

### Mode A — Prompt Export

AIOS creates an evidence-grounded prompt pack containing:
- goal/question;
- evidence pack;
- source refs;
- allowed actions;
- privacy mode;
- expected answer format;
- warnings and non-goals.

Privacy:
- company/mật: local-only/trusted-model only; external export blocked unless user explicitly marks safe;
- tài liệu thường: cloud-safe prompt export allowed.

### Mode B — Paste-back Answer

User pastes output from Codex/Gemini/Claude/GPT/Opus/IDE.

AIOS stores:
- model/tool name;
- prompt pack ID;
- answer;
- evidence refs;
- route summary;
- external AI used yes/no;
- warnings/confidence;
- case link;
- created time.

### Mode C — Tool/IDE Adapter Later

Adapters can include:
- Codex CLI adapter;
- Gemini API/CLI adapter;
- Claude API/CLI adapter;
- OpenAI-compatible adapter;
- local-only adapter.

Rules:
- approval gate before file edit/action;
- no automatic agent writes without user approval;
- no raw secrets in logs;
- no provider calls for company/mật unless trusted/local rules are satisfied.

### Mode D — Agent Harness

Harness state:
- task state;
- evidence state;
- tool permission;
- context compaction;
- subtask delegation;
- audit log;
- rollback/handoff;
- final validation checklist.

Design principle: AIOS should learn from Claude-Code-style loops, Cline approval gates, Aider git discipline, OpenHands isolation, LangGraph state, and Letta memory tiers without copying source or surrendering local-first control.

## Privacy Model

Privacy modes:
- `local_only`: never exported to cloud/provider;
- `cloud_safe`: allowed for normal documents;
- `trusted_internal`: allowed only for explicitly configured local/trusted endpoint;
- `redacted_export`: only redacted snippets exported.

Required controls:
- explicit safety mode on every evidence pack;
- prompt export checks;
- paste-back answer labeling;
- route log with external sent yes/no;
- no API key display;
- no raw provider payload persisted unless safe and approved;
- ignored runtime artifacts remain untracked.

## Implementation Gates

1. **AIOS-RAG-INGEST-1**
   - Improve parser/chunk metadata only.
   - No vector DB.
   - No cloud OCR.
   - Tests for PDF/Excel/PPTX/image/source refs.

2. **AIOS-RAG-SEARCH-1**
   - SQLite FTS/BM25 local hybrid foundation.
   - Metadata filters.
   - Ranking tests.
   - No external model dependency.

3. **AIOS-RAG-EVIDENCE-PACK-1**
   - Evidence pack builder.
   - Source scoring.
   - Insufficient evidence handling.
   - Attach pack to answer/case.

4. **AIOS-IDE-BRIDGE-1**
   - Manual prompt export.
   - Paste-back answer.
   - Model/tool/evidence/route summary saved.
   - No API automation yet.

5. **AIOS-RAG-BENCHMARK-1**
   - Compare AIOS vs NotebookLM on same non-sensitive docs/questions.
   - No fake parity.

Later:
- AIOS-RAG-RERANK-1;
- AIOS-CASE-SCALE-1;
- AIOS-WORKSTREAM-MAP-1;
- AIOS-P1-READINESS-CHECKLIST.

## Risks

- Overbuilding a graph/vector stack before the local FTS baseline is measured.
- Losing local-first safety by adding cloud OCR/embedding/rerank too early.
- Fake parity claims versus NotebookLM before benchmark evidence exists.
- Prompt exports accidentally including company/mật evidence.
- Agent automation editing files or running tools without approval.
- Runtime artifacts or secrets becoming tracked.

## Explicit Non-goals

- No implementation in this gate.
- No vector DB or graph DB added now.
- No provider/cloud call.
- No API key read or printed.
- No P1.0 opened.
- No NotebookLM parity claim.
- No leaked/proprietary source copying.
- No ML/prediction engine.

## Recommendation

Proceed with `AIOS-RAG-INGEST-1` first. The highest-leverage next move is to normalize parser output and chunk metadata so every later feature can rely on stable document/chunk IDs, citations, privacy flags, and source structure. Then add SQLite FTS/BM25 search, evidence packs, manual IDE bridge, and only then benchmark against NotebookLM.
