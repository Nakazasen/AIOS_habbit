# AIOS Product Positioning

## Mission

AIOS WorkLens / AIOS_habbit là một **hệ điều hành trí nhớ công việc cá nhân, local-first**. Mục tiêu là biến bằng chứng công việc hằng ngày thành tri thức có thể tái sử dụng:

```text
Case → Evidence → Map → Action → Learning → Memory
```

AIOS không chỉ hỏi đáp tài liệu. AIOS phải giúp người dùng làm việc thật với tài liệu, Excel, ảnh, log, chat, email, AI output và sự việc hằng ngày; sau đó lưu lại mô hình làm việc, bài học, evidence, route log, privacy mode và công cụ/model đã dùng.

## AIOS không phải là

- Không phải chat backup.
- Không phải chatbot RAG đơn giản.
- Không phải chỉ là clone NotebookLM.
- Không phải production prediction engine.
- Không phải công cụ upload tài liệu công ty lên cloud.
- Không phải hệ thống traceability chỉ dành cho LSU.

## Nguyên tắc sản phẩm

- Không lưu hội thoại nếu không cần; ưu tiên lưu tri thức đã được cấu trúc.
- Không chỉ lưu câu chữ; lưu mô hình làm việc, quyết định và bài học.
- Không phụ thuộc riêng ChatGPT, Gemini, Claude, NotebookLM hay DeepSeek.
- Dữ liệu công ty/mật mặc định local-first và không gửi ra ngoài.
- Mọi câu trả lời quan trọng phải trace được evidence, route log, model/tool đã dùng và privacy mode.
- Model mạnh chỉ là một phần; chất lượng phụ thuộc parser, index, retrieval, rerank, evidence pack, context và privacy guard.

## Trạng thái hiện tại

- Phase 0 — Vision & Governance: DONE.
- Phase 1 — Local Case Cockpit Foundation: DONE.
- Phase 2 — Real Document / MOM Foundation: DONE_WITH_WARNINGS.
- Phase 3 — Provider Safety + Daily UI: DONE_WITH_WARNINGS.
- Vị trí hiện tại: cuối Phase 3, trước Phase 4 RAG Engine v2 và Phase 5 IDE/model bridge.
- P1.0: LOCKED, chưa mở.
- NotebookLM parity: chưa đạt và không được fake.
- IDE/model bridge: chưa implemented.

## Phase roadmap

### Phase 4 — RAG Engine v2 / NotebookLM-level Retrieval

Status: NEXT.

Scope:
- better parser adapter
- structure-aware chunks
- SQLite FTS / BM25
- optional embeddings later
- hybrid search
- rerank
- query rewrite
- evidence pack
- citation scoring
- NotebookLM-style benchmark

Not allowed yet:
- heavy vector DB without decision
- cloud embedding for company/mật
- fake NotebookLM parity claim

### Phase 5 — IDE / Strong Model Answer Bridge

Status: NEXT_PARALLEL.

Scope:
- export prompt pack
- use Codex/Gemini/Claude/GPT/Opus in external IDE/chat
- paste-back answer
- store model/tool name
- store evidence refs
- store route summary
- privacy guard

Not allowed yet:
- direct cloud call for company/mật
- raw API keys in UI/logs
- automatic agent edits without approval

### Later phases

- Phase 6 — Case Memory at Scale.
- Phase 7 — Work Stream Map / Knowledge Graph.
- Phase 8 — Senior Learning / Personal OS.
- Phase 9 — Production Traceability Foundation.
- Phase 10 — P1.0 Production Readiness.

## Learning sources for future design research

Use public design patterns only; do not copy leaked/proprietary code.

- RAGFlow
- kotaemon
- Microsoft GraphRAG
- LightRAG
- LlamaIndex
- Haystack
- Docling
- Unstructured
- OpenHands
- Aider
- Cline
- Continue
- Goose
- Cognee
- Letta / MemGPT
- LangGraph
- Semantic Kernel

## Next gate queue

Immediate:
1. AIOS-RAG-AGENT-HARNESS-0 — research RAG + Claude-Code-style harness patterns, docs only.
2. AIOS-RAG-INGEST-1 — improve parser/chunk metadata, no vector DB yet.
3. AIOS-RAG-SEARCH-1 — local hybrid search foundation, SQLite FTS/BM25, metadata filters, citation IDs.
4. AIOS-RAG-EVIDENCE-PACK-1 — evidence pack builder, source scoring, answer abstention.
5. AIOS-IDE-BRIDGE-1 — manual prompt export, paste-back answer, store model/tool/evidence/route log.

Later:
6. AIOS-RAG-RERANK-1
7. AIOS-RAG-BENCHMARK-1
8. AIOS-CASE-SCALE-1
9. AIOS-WORKSTREAM-MAP-1
10. AIOS-P1-READINESS-CHECKLIST
