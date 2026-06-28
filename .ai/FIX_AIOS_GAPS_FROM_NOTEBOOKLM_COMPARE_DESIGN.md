# Fix AIOS Gaps from NotebookLM Compare Design

## Context
Following the 2Q comparison against NotebookLM MCP, AIOS tied closely on factual understanding but lost by 1 point due to weaker source traceability, lack of inline citations, and less explicit limitation analysis. 

## Constraints
* AIOS source selection already passed (both Q1 and Q2).
* **DO NOT** fix gaps by causing broad retrieval churn. The RAG engine is working well.
* Main fix is focused entirely on **citation-first answer composition**.
* Do not claim global NotebookLM parity.
* Do not open P1.0.

## Citation-First Answer Composition Model
Every generated answer must follow this structured template:
1. **Trả lời ngắn** (Short answer summary)
2. **Bằng chứng chính** (Evidence-backed bullets)
3. **Trích dẫn nội tuyến** (Inline evidence references like `[E1]`, `[E2]`)
4. **Phân tích** (Analysis grounded in the cited sources)
5. **Không được suy luận quá mức** (Limitation / what not to infer)
6. **Việc cần làm tiếp** (Next action)
7. **Bảng nguồn** (Source traceability table)

## Special Handling by Evidence Type

### Screenshot / HTML / ERD
Must explicitly separate visible facts from inferred business logic.
* **Nhìn thấy trực tiếp:** Các trường, cột, quan hệ có trên ảnh.
* **Có thể dùng làm bằng chứng tĩnh.**
* **Không được suy luận nếu chỉ có ảnh/sơ đồ:** Logic nghiệp vụ, thứ tự phê duyệt, hay thực trạng dữ liệu bị lỗi vật lý.

### PDF / PPTX
Must explain the boundary between automation and manual work with citations.
* **Tự động xử lý:** Những điểm hệ thống tự động ghi nhận (ví dụ: qua Oricon Gate).
* **Cần xử lý thủ công / owner review:** Những điểm công nhân/owner phải thao tác bằng tay (quét mã HT, review lỗi thiết bị, phê duyệt QA).

## Implementation Plan
1. **Create `src/aios_habit/citation_answer.py`**:
   - `build_citation_index(evidence_items)`: Map items to stable [E1], [E2] refs.
   - `format_inline_citation(evidence_ref)`: Format the ref string.
   - `compose_citation_first_answer(...)`: Build the structured output.
   - `extract_visible_vs_inferred_claims(...)`: Handle limitation extraction.
   - `build_source_traceability_table(...)`: Generate markdown table of sources.
   - `score_citation_coverage(...)`: Metric checking.

2. **Integrate into Answer Flow**:
   - Update `src/aios_habit/rag_answer_composer.py` to use `citation_answer.py` for local drafts.
   - Update `src/aios_habit/ide_handoff_bridge.py` and `ide_bridge.py` prompts to enforce citation-first answers from external models.
   - Update `src/aios_habit/case_cockpit.py` to correctly render the structured format and source table in the UI.
