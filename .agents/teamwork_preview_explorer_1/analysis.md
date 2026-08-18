# Comprehensive Architectural & Translation Survey: `layers`, `tour`, and Root Structure

**File Target**: `.understand-anything/knowledge-graph.json`  
**Explorer**: `teamwork_preview_explorer_1`  
**Date**: 2026-08-19  
**Status**: COMPLETE  

---

## 1. Executive Summary

File `.understand-anything/knowledge-graph.json` là tệp dữ liệu trung tâm định nghĩa đồ thị tri thức (Knowledge Graph) phục vụ visualization và dashboard kiến trúc của hệ thống `AIOS_habbit`. 

Qua khảo sát toàn diện:
- File có tổng cộng **2.663 dòng**, kích thước **92.229 bytes**, mã hóa **UTF-8**.
- Cấu trúc gốc gồm **6 khóa chính (root keys)**: `version`, `project`, `nodes`, `edges`, `layers`, `tour`.
- Mảng `layers` gồm đúng **8 tầng kiến trúc (layers)** với các trường cần dịch là `name` và `description`; các trường `id` và `nodeIds` bắt buộc **giữ nguyên 100%**.
- Mảng `tour` gồm đúng **9 bước hướng dẫn (steps)** với các trường cần dịch là `title` và `description`; các trường `order` và `nodeIds` bắt buộc **giữ nguyên 100%**.
- Dự án đã có sẵn quy chuẩn thuật ngữ tại `docs/governance/LOCALIZATION_GLOSSARY.md` và `01_design/TERMINOLOGY.md`. Cần tuân thủ triệt để nguyên tắc: giữ nguyên các thuật ngữ IT cốt lõi (Agent, Local Storage, Orchestration, Framework, Dashboard, Streamlit, Pydantic, v.v.) và chuẩn hóa các thuật ngữ bản địa theo quy chuẩn dự án (Bằng chứng, Nguồn dữ liệu, Kho bộ nhớ, Cổng kiểm soát giai đoạn, v.v.).

---

## 2. Root Structure & Key Specification

| Root Key | Kiểu dữ liệu | Số lượng phần tử / Nội dung | Mục đích kiến trúc | Phạm vi dịch (Translate Scope) |
|---|---|---|---|---|
| `version` | `string` | `"1.0.0"` | Phiên bản schema của knowledge graph | **GIỮ NGUYÊN** |
| `project` | `object` | 6 thuộc tính (`name`, `languages`, `frameworks`, `description`, `analyzedAt`, `gitCommitHash`) | Metadata của dự án | Dịch `description` (hoặc giữ nguyên nếu schema đòi hỏi metadata tĩnh). Các trường `name`, `languages`, `frameworks`, `analyzedAt`, `gitCommitHash` **GIỮ NGUYÊN**. |
| `nodes` | `array` | 727 node objects | Danh sách file, tài liệu, module trong hệ thống | Chỉ dịch trường `summary` (R2 - do explorer 2 & implementers phụ trách). `id`, `type`, `name`, `filePath`, `tags`, `complexity` **GIỮ NGUYÊN**. |
| `edges` | `array` | 350 edge objects | Mối quan hệ liên kết giữa các node (`references`, `related`, v.v.) | **GIỮ NGUYÊN 100%** |
| `layers` | `array` | 8 layer objects | Phân tầng kiến trúc hệ thống | **DỊCH** `name`, `description`. `id` và `nodeIds` **GIỮ NGUYÊN**. |
| `tour` | `array` | 9 tour step objects | Lộ trình tour hướng dẫn khám phá kiến trúc từng bước | **DỊCH** `title`, `description`. `order` và `nodeIds` **GIỮ NGUYÊN**. |

### Chi tiết đối tượng `project`:
```json
{
  "name": "aios-habit",
  "languages": ["python", "markdown", "json"],
  "frameworks": ["streamlit", "pydantic"],
  "description": "Local-first evidence-based personal memory platform",
  "analyzedAt": "2026-08-18T23:08:53.818Z",
  "gitCommitHash": "HEAD"
}
```
*Đề xuất dịch `project.description`*: `"Nền tảng bộ nhớ cá nhân ưu tiên cục bộ (local-first) dựa trên bằng chứng"` (hoặc giữ nguyên nếu tool sinh metadata tự động).

---

## 3. Detailed Analysis of `layers` Array

Mảng `layers` nằm từ dòng 2094 đến dòng 2550 trong `knowledge-graph.json`.
Gồm **8 phần tử**.

### Schema của mỗi phần tử `layers[i]`:
- `id` (`string`): Định danh định tuyến duy nhất dạng `layer:<slug>` (Ví dụ: `layer:presentation-ui`). **QUY TẮC: BẢO TOÀN NGUYÊN VẸN 100%**. Dashboard JS sử dụng ID này để filter và highlight nodes.
- `name` (`string`): Tên hiển thị của tầng kiến trúc. **QUY TẮC: DỊCH SANG TIẾNG VIỆT CHUẨN**, giữ thuật ngữ chính hoặc dùng dạng song ngữ / ngoặc đơn nếu cần thiết để đảm bảo sự rõ ràng.
- `description` (`string`): Mô tả chi tiết chức năng và phạm vi kỹ thuật của tầng. **QUY TẮC: DỊCH SANG TIẾNG VIỆT TOÀN DIỆN**, bảo toàn các thuật ngữ IT chuyên ngành.
- `nodeIds` (`array of strings`): Danh sách ID các node thuộc tầng này. **QUY TẮC: BẢO TOÀN NGUYÊN VẸN 100%**. Không thay đổi đường dẫn hay thứ tự.

### Bảng phân tích chi tiết 8 Layers & Bản dịch Đề xuất

#### Layer 1: `layer:presentation-ui`
- **Node count**: 7 nodes
- **Original Name**: `Presentation & UI Layer`
- **Original Description**: `User interfaces, Streamlit web application components, CLI entry points, and visual rendering dashboards.`
- **Proposed Vietnamese Name**: `Tầng Trình diễn & Giao diện người dùng (Presentation & UI Layer)`
- **Proposed Vietnamese Description**: `Giao diện người dùng, các thành phần ứng dụng web Streamlit, điểm vào CLI, và các dashboard hiển thị đồ họa trực quan.`
- **Preserved Terms**: `Streamlit`, `CLI`, `dashboard`, `Presentation & UI Layer`

#### Layer 2: `layer:orchestration-agents`
- **Node count**: 12 nodes
- **Original Name**: `Orchestration & Agent Coordination Layer`
- **Original Description**: `Multi-agent orchestration, IDE integration bridges, task package distribution, handovers, agent continuous learning, and automated workflows.`
- **Proposed Vietnamese Name**: `Tầng Điều phối Orchestration & Phối hợp Agent`
- **Proposed Vietnamese Description**: `Điều phối Multi-agent (đa agent), cầu nối tích hợp IDE, phân phối gói tác vụ (task pack), bàn giao (handover), học liên tục cho agent, và các workflow tự động.`
- **Preserved Terms**: `Orchestration`, `Agent`, `Multi-agent`, `IDE`, `task pack`, `handover`, `workflow`

#### Layer 3: `layer:intelligence-routing`
- **Node count**: 10 nodes
- **Original Name**: `Intelligence & AI Routing Layer`
- **Original Description**: `AI provider routing, LLM client abstractions, brain gateway privacy protection, answer composition, citation grounding, claim verification, and benchmark comparisons.`
- **Proposed Vietnamese Name**: `Tầng Trí tuệ & Định tuyến AI (Intelligence & AI Routing Layer)`
- **Proposed Vietnamese Description**: `Định tuyến AI provider, trừu tượng hóa LLM client, bảo vệ quyền riêng tư qua Brain Gateway, tổng hợp câu trả lời, đối chiếu trích dẫn (citation grounding), kiểm chứng khẳng định (claim verification), và so sánh benchmark.`
- **Preserved Terms**: `AI provider`, `LLM client`, `Brain Gateway`, `citation grounding`, `claim verification`, `benchmark`

#### Layer 4: `layer:knowledge-retrieval`
- **Node count**: 15 nodes
- **Original Name**: `Knowledge, Retrieval & Ingestion Layer`
- **Original Description**: `Evidence extraction engines, deep document/Excel parsers, OCR, lexical and graph indices, MoM local indexing, and reference acquisition.`
- **Proposed Vietnamese Name**: `Tầng Tri thức, Truy xuất & Thu nạp Dữ liệu (Knowledge, Retrieval & Ingestion Layer)`
- **Proposed Vietnamese Description**: `Bộ máy trích xuất bằng chứng, trình phân tích tài liệu/Excel chuyên sâu, OCR, chỉ mục từ vựng và đồ thị (graph index), lập chỉ mục cục bộ MoM, và thu thập tài liệu tham chiếu.`
- **Preserved Terms**: `OCR`, `Excel`, `graph index`, `MoM`, `retrieval`, `ingestion`

#### Layer 5: `layer:data-storage`
- **Node count**: 47 nodes
- **Original Name**: `Data & Persistence Layer`
- **Original Description**: `Core data models, JSONL and SQLite local storage engines, memory vault units, evidence registry, case repositories, profile management, and JSON schema definitions.`
- **Proposed Vietnamese Name**: `Tầng Dữ liệu & Lưu trữ Bền vững (Data & Persistence Layer)`
- **Proposed Vietnamese Description**: `Các data model cốt lõi, công cụ Local Storage định dạng JSONL và SQLite, các đơn vị kho bộ nhớ (memory vault), sổ đăng ký bằng chứng (evidence registry), kho lưu trữ ca xử lý (case store), quản lý hồ sơ profile, và định nghĩa JSON schema.`
- **Preserved Terms**: `data model`, `JSONL`, `SQLite`, `Local Storage`, `memory vault`, `evidence registry`, `case store`, `profile`, `JSON schema`

#### Layer 6: `layer:testing-quality`
- **Node count**: 71 nodes
- **Original Name**: `Testing & Quality Assurance Layer`
- **Original Description**: `Automated unit tests, integration test suites, evaluation harnesses, RAG benchmarking test suites, and regression guards.`
- **Proposed Vietnamese Name**: `Tầng Kiểm thử & Đảm bảo Chất lượng (Testing & Quality Assurance Layer)`
- **Proposed Vietnamese Description**: `Kiểm thử đơn vị tự động (unit tests), bộ kiểm thử tích hợp (integration tests), khung đánh giá (evaluation harness), bộ kiểm thử benchmark RAG, và các chốt chặn chống thoái lui (regression guards).`
- **Preserved Terms**: `unit tests`, `integration tests`, `evaluation harness`, `RAG benchmark`, `regression guards`

#### Layer 7: `layer:specifications-tooling`
- **Node count**: 45 nodes
- **Original Name**: `Specifications & Tooling Layer`
- **Original Description**: `Feature specifications, Spec-Kit development automation scripts, markdown artifact templates, and development tooling metadata.`
- **Proposed Vietnamese Name**: `Tầng Đặc tả Yêu cầu & Công cụ Phát triển (Specifications & Tooling Layer)`
- **Proposed Vietnamese Description**: `Đặc tả tính năng (feature specifications), script tự động hóa phát triển Spec-Kit, biểu mẫu artifact Markdown, và siêu dữ liệu công cụ phát triển.`
- **Preserved Terms**: `feature specifications`, `Spec-Kit`, `artifact`, `Markdown`, `script`

#### Layer 8: `layer:governance-documentation`
- **Node count**: 196 nodes
- **Original Name**: `Governance, Architecture & Operational Records Layer`
- **Original Description**: `Project constitution, governance standards, architectural decision records (ADRs), phase gate audits, operational runbooks, agent interaction records, and benchmark studies.`
- **Proposed Vietnamese Name**: `Tầng Quản trị, Kiến trúc & Hồ sơ Vận hành (Governance, Architecture & Operational Records Layer)`
- **Proposed Vietnamese Description**: `Hiến pháp dự án (constitution), tiêu chuẩn quản trị, hồ sơ quyết định kiến trúc (ADRs), kiểm toán cổng giai đoạn (phase gate audits), cẩm nang vận hành (runbooks), nhật ký tương tác agent, và các nghiên cứu benchmark.`
- **Preserved Terms**: `constitution`, `ADRs`, `phase gate audits`, `runbooks`, `agent`, `benchmark`

---

## 4. Detailed Analysis of `tour` Array

Mảng `tour` nằm từ dòng 2551 đến dòng 2662 trong `knowledge-graph.json`.
Gồm đúng **9 bước (tour steps)**.

### Schema của mỗi phần tử `tour[i]`:
- `order` (`integer`): Thứ tự của bước hướng dẫn (từ 1 đến 9). **QUY TẮC: BẢO TOÀN NGUYÊN VẸN**.
- `title` (`string`): Tiêu đề ngắn gọn của bước tour. **QUY TẮC: DỊCH SANG TIẾNG VIỆT CHUẨN**, giữ thuật ngữ IT cốt lõi.
- `description` (`string`): Đoạn văn mô tả hướng dẫn, giải thích ý nghĩa kiến trúc và các file trọng tâm. **QUY TẮC: DỊCH SANG TIẾNG VIỆT MƯỢT MÀ**, giữ thuật ngữ kỹ thuật.
- `nodeIds` (`array of strings`): Danh sách file tiêu biểu được highlight trong bước tour. **QUY TẮC: BẢO TOÀN NGUYÊN VẸN 100%**.

### Bảng phân tích chi tiết 9 Tour Steps & Bản dịch Đề xuất

#### Step 1 (`order: 1`):
- **Node count**: 5 nodes (`README.md`, `CONSTITUTION.md`, `ARCHITECTURE.md`, `00_governance/DATA_POLICY.md`, `docs/adr/0001-local-first-filesystem-ownership.md`)
- **Original Title**: `System Overview, Governance & Architecture`
- **Original Description**: `Start with the project documentation to understand AIOS_habbit's core mission as a local-first, evidence-based personal memory platform. Explore the architectural constitution, strict local data governance rules, and core Architectural Decision Records (ADRs) that mandate zero data leakage and un-hallucinated memory storage.`
- **Proposed Vietnamese Title**: `Tổng quan Hệ thống, Quản trị & Kiến trúc`
- **Proposed Vietnamese Description**: `Bắt đầu với tài liệu dự án để hiểu sứ mệnh cốt lõi của AIOS_habbit như một nền tảng bộ nhớ cá nhân ưu tiên cục bộ (local-first) dựa trên bằng chứng thực tế. Khám phá hiến pháp kiến trúc, các quy tắc quản trị dữ liệu cục bộ nghiêm ngặt, và các Hồ sơ Quyết định Kiến trúc (ADRs) cốt lõi nhằm đảm bảo không rò rỉ dữ liệu và lưu trữ bộ nhớ không bị ảo giác (un-hallucinated).`

#### Step 2 (`order: 2`):
- **Node count**: 7 nodes (`src/aios_habit/models.py`, `evidence.py`, `memory.py`, `local_jsonl.py`, `storage.py`, `case_models.py`, `case_store.py`)
- **Original Title**: `Core Data Models & Local Storage`
- **Original Description**: `Examine the foundational data schemas and persistence engines. Understand how Evidence Records (source snippets, confidence, provenance) and Memory Units (behavior, identity, decisions, lessons learned) are structured in Pydantic models and stored safely in local JSONL records and modular memory vaults.`
- **Proposed Vietnamese Title**: `Mô hình Dữ liệu Cốt lõi & Local Storage`
- **Proposed Vietnamese Description**: `Xem xét các schema dữ liệu nền tảng và công cụ lưu trữ bền vững. Tìm hiểu cách các Bản ghi Bằng chứng (đoạn trích nguồn, độ tin cậy, nguồn gốc) và Đơn vị Bộ nhớ (hành vi, danh tính, quyết định, bài học kinh nghiệm) được cấu trúc trong Pydantic model và lưu trữ an toàn trong các bản ghi JSONL cục bộ cùng các kho bộ nhớ (memory vault) mô-đun.`

#### Step 3 (`order: 3`):
- **Node count**: 5 nodes (`extraction.py`, `document_extractors.py`, `excel_extractors.py`, `deep_document_parsers.py`, `extractor_registry.py`)
- **Original Title**: `Document Ingestion & Multi-Format Extraction`
- **Original Description**: `Discover how raw user materials are ingested across formats (PDF, DOCX, XLSX, TXT, OCR images). The extraction engine cleans, structures, and extracts tabular and narrative data with deterministic offsets and metadata preservation.`
- **Proposed Vietnamese Title**: `Thu nạp Tài liệu & Trích xuất Đa Định dạng`
- **Proposed Vietnamese Description**: `Khám phá cách tài liệu thô của người dùng được thu nạp qua nhiều định dạng (PDF, DOCX, XLSX, TXT, hình ảnh OCR). Bộ máy trích xuất làm sạch, cấu trúc hóa và trích xuất dữ liệu dạng bảng cũng như văn bản tự sự với vị trí offset xác định và bảo toàn siêu dữ liệu (metadata).`

#### Step 4 (`order: 4`):
- **Node count**: 4 nodes (`mom_local_index.py`, `notebook_index.py`, `notebook_graph.py`, `notebook_bridge.py`)
- **Original Title**: `Local Indexing, Search & Graph Retrieval (RAG v2)`
- **Original Description**: `Trace the local retrieval pipeline. Ingested knowledge is indexed via SQLite full-text search (BM25), chunking adapters, knowledge graphs, and adaptive re-ranking to deliver high-precision evidence lookup without cloud dependency.`
- **Proposed Vietnamese Title**: `Lập Chỉ mục Cục bộ, Tìm kiếm & Truy xuất Đồ thị (RAG v2)`
- **Proposed Vietnamese Description**: `Theo dõi quy trình truy xuất cục bộ. Tri thức đã thu nạp được lập chỉ mục qua tìm kiếm toàn văn SQLite (BM25), adapter phân mảnh (chunking), đồ thị tri thức (knowledge graph), và xếp hạng lại thích ứng (adaptive re-ranking) nhằm cung cấp khả năng tra cứu bằng chứng độ chính xác cao mà không phụ thuộc vào đám mây.`

#### Step 5 (`order: 5`):
- **Node count**: 5 nodes (`ai_router.py`, `ai_provider_bridge.py`, `llm_client.py`, `brain_gateway.py`, `docs/adr/0004-brain-gateway-privacy-ownership.md`)
- **Original Title**: `Intelligence Routing & Brain Gateway`
- **Original Description**: `Explore the multi-model intelligence dispatcher. Learn how queries are intelligently routed between local models (Ollama/LMStudio) and external LLM providers, with the Brain Gateway sanitizing and guarding sensitive user context.`
- **Proposed Vietnamese Title**: `Định tuyến Trí tuệ AI & Brain Gateway`
- **Proposed Vietnamese Description**: `Khám phá bộ điều phối trí tuệ đa mô hình. Tìm hiểu cách các truy vấn được định tuyến thông minh giữa các mô hình cục bộ (Ollama/LMStudio) và nhà cung cấp LLM bên ngoài, trong đó Brain Gateway làm sạch và bảo vệ ngữ cảnh nhạy cảm của người dùng.`

#### Step 6 (`order: 6`):
- **Node count**: 5 nodes (`citation_answer.py`, `final_answer_composer.py`, `claim_guard.py`, `notebook_qa.py`, `notebooklm_compare.py`)
- **Original Title**: `Citation Grounding & Claim Guard`
- **Original Description**: `See how AIOS_habbit ensures truthfulness. The Final Answer Composer synthesizes answers containing strict verbatim citations, while Claim Guard verifies that claims are directly supported by evidence chunks and benchmarks against Google NotebookLM.`
- **Proposed Vietnamese Title**: `Đối chiếu Trích dẫn & Claim Guard (Kiểm chứng Khẳng định)`
- **Proposed Vietnamese Description**: `Xem cách AIOS_habbit đảm bảo tính chân thực (truthfulness). Final Answer Composer tổng hợp các câu trả lời chứa trích dẫn nguyên văn nghiêm ngặt, trong khi Claim Guard xác minh các khẳng định được chứng minh trực tiếp bởi các đoạn bằng chứng và so sánh benchmark với Google NotebookLM.`

#### Step 7 (`order: 7`):
- **Node count**: 6 nodes (`workspace_agent_orchestrator.py`, `antigravity_bridge.py`, `ide_bridge.py`, `ide_handoff_bridge.py`, `agent_task_pack.py`, `agent_learning.py`)
- **Original Title**: `Agent Orchestration & IDE Bridges`
- **Original Description**: `Understand developer workflows and agent collaboration. AIOS_habbit connects directly into IDE environments (Antigravity, Cursor, VS Code), packaging task contexts, managing handoffs, and continuously learning from agent outcomes.`
- **Proposed Vietnamese Title**: `Điều phối Agent & Cầu nối IDE`
- **Proposed Vietnamese Description**: `Hiểu quy trình làm việc của lập trình viên và sự cộng tác giữa các agent. AIOS_habbit kết nối trực tiếp vào các môi trường IDE (Antigravity, Cursor, VS Code), đóng gói ngữ cảnh tác vụ (task pack), quản lý bàn giao (handoff), và liên tục học hỏi từ kết quả thực thi của agent.`

#### Step 8 (`order: 8`):
- **Node count**: 5 nodes (`workspace_chat_app.py`, `workspace_chat_ui.py`, `cli.py`, `knowledge_map_view.py`, `knowledge_map_html.py`)
- **Original Title**: `Presentation UI & Interactive Knowledge Maps`
- **Original Description**: `Explore the user-facing layer: a Streamlit-based Workspace Chat application with source library management, note-taking notebooks, CLI interfaces, and interactive HTML visual graph renderers.`
- **Proposed Vietnamese Title**: `Giao diện Trình diễn & Bản đồ Tri thức Tương tác`
- **Proposed Vietnamese Description**: `Khám phá tầng giao diện người dùng: ứng dụng Workspace Chat dựa trên Streamlit với tính năng quản lý thư viện nguồn dữ liệu, sổ tay ghi chú (notebooks), giao diện dòng lệnh CLI, và trình kết xuất đồ thị trực quan HTML tương tác.`

#### Step 9 (`order: 9`):
- **Node count**: 5 nodes (`specs/001-stage-a-resume-guard/spec.md`, `specs/003-adaptive-reranking-ux/spec.md`, `tests/test_rag_benchmark.py`, `tests/test_workspace_chat_owner_flow.py`, `tests/test_final_answer_composer.py`)
- **Original Title**: `Specifications, Benchmarking & Quality Assurance`
- **Original Description**: `Inspect how features are specified and verified. Spec-Kit specifications drive implementation phases, while evaluation harnesses, benchmark suites, and regression tests enforce strict evidence and UI contracts.`
- **Proposed Vietnamese Title**: `Đặc tả Kỹ thuật, Benchmarking & Đảm bảo Chất lượng`
- **Proposed Vietnamese Description**: `Kiểm tra cách các tính năng được đặc tả và xác minh. Các đặc tả Spec-Kit định hướng các giai đoạn triển khai, trong khi các khung đánh giá (evaluation harness), bộ kiểm thử benchmark và kiểm thử chống thoái lui (regression tests) thực thi nghiêm ngặt các giao ước về bằng chứng và giao diện UI.`

---

## 5. Domain-Specific IT Terminology & Glossary Matrix

Dựa trên khảo sát codebase cùng 2 tài liệu chuẩn:
1. `docs/governance/LOCALIZATION_GLOSSARY.md`
2. `01_design/TERMINOLOGY.md`

Dưới đây là ma trận phân loại thuật ngữ IT cho toàn bộ quá trình dịch thuật JSON:

### Nhóm 1: Thuật ngữ IT cốt lõi BẮT BUỘC GIỮ NGUYÊN TIẾNG ANH
Các thuật ngữ này không dịch hoặc chỉ chú thích phụ trong ngoặc đơn:
- **Kiến trúc & Tác nhân**: `Agent`, `Multi-agent`, `Orchestrator`, `Orchestration`, `Framework`, `Dashboard`, `IDE`, `CLI`, `Workflow`, `Pipeline`, `Bridge`, `Adapter`.
- **Lưu trữ & Dữ liệu**: `Local Storage`, `JSONL`, `SQLite`, `Pydantic`, `JSON Schema`, `Schema`, `Offset`, `Metadata`, `Memory Vault`, `Cache`.
- **Trí tuệ nhân tạo & Truy xuất**: `LLM`, `RAG`, `BM25`, `Embedding`, `Chunking`, `Re-ranking`, `Adaptive re-ranking`, `Grounding`, `Citation Grounding`, `Prompt`, `Token`.
- **Tên Component / Hệ thống riêng**: `AIOS_habbit`, `Brain Gateway`, `Claim Guard`, `Final Answer Composer`, `Workspace Chat`, `Spec-Kit`, `Antigravity`, `Streamlit`, `NotebookLM`, `Ollama`, `LMStudio`.
- **Kiểm thử & Quản trị**: `Unit test`, `Integration test`, `Evaluation harness`, `Benchmark`, `Regression guard`, `ADR` (Architectural Decision Record), `Phase Gate`, `Runbook`.

### Nhóm 2: Thuật ngữ đã được chuẩn hóa sang Tiếng Việt trong dự án
| Thuật ngữ gốc | Bản dịch Tiếng Việt chuẩn hóa | Ghi chú & Ngữ cảnh |
|---|---|---|
| `evidence` / `evidence record` | `bằng chứng` / `bản ghi bằng chứng` | Dữ liệu chứng cứ có nguồn gốc đã trích xuất |
| `source` / `raw source` | `nguồn` / `nguồn dữ liệu thô` | Tài liệu, file gốc đưa vào hệ thống |
| `candidate memory` | `bộ nhớ ứng viên` | Bộ nhớ mới trích xuất chưa thẩm định |
| `validated memory` | `bộ nhớ đã xác thực` | Bộ nhớ đã qua kiểm định |
| `master profile` | `hồ sơ tổng thể` | Hồ sơ tổng hợp danh tính, hành vi, quy trình |
| `export pack` | `gói xuất` | Bản chuyển đổi định dạng riêng cho AI khác |
| `phase gate` | `cổng kiểm soát giai đoạn` | Điểm kiểm soát chất lượng bàn giao |
| `privacy label` | `nhãn bảo mật` | Nhãn phân loại dữ liệu (local_only, confidential...) |
| `insufficient evidence` | `chưa đủ bằng chứng` | Trạng thái thiếu căn cứ chứng minh |
| `fallback` | `phương án dự phòng` | Cơ chế dự phòng khi lỗi/không tìm thấy |
| `un-hallucinated` / `truthfulness` | `không bị ảo giác` / `tính chân thực` | Đảm bảo tính xác thực dựa trên bằng chứng |
| `local-first` | `ưu tiên cục bộ` (hoặc `local-first`) | Triết lý dữ liệu nằm tại máy người dùng |

---

## 6. Implementation Guardrails for Merging & Synthesis

Khi các worker và orchestrator tiến hành dịch và ghi đè vào `.understand-anything/knowledge-graph.json`:
1. **JSON Schema & Syntax Validity**:
   - Sử dụng đúng cấu trúc JSON, không để trailing commas.
   - Escape chính xác các ký tự đặc biệt (`"` -> `\"`, `\n` nếu có trong chuỗi).
2. **Key Preservation**:
   - Không thay đổi bất kỳ key name nào (`version`, `project`, `nodes`, `edges`, `layers`, `tour`, `id`, `nodeIds`, `type`, `order`, v.v.).
3. **Reference Integrity**:
   - Mọi chuỗi trong mảng `nodeIds` của `layers` và `tour` phải trỏ chính xác đến các `id` tồn tại trong mảng `nodes`.
4. **Encoding**:
   - Phải lưu dưới dạng UTF-8 không BOM (UTF-8 without BOM) để JavaScript / JSON.parse và dashboard HTML/Streamlit đọc mượt mà không lỗi font tiếng Việt.
5. **Verification Method**:
   - Chạy kiểm tra cú pháp JSON bằng node/python.
   - Kiểm tra `layers.length === 8` và `tour.length === 9`.
   - Kiểm tra không có `nodeId` mồ côi (orphaned node reference).

---
*Báo cáo được hoàn thành bởi `teamwork_preview_explorer_1`.*
