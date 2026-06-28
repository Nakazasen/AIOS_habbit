# NotebookLM MCP vs AIOS 2Q Rerun Report (After Citation Fix)

* **Branch:** main
* **NotebookLM MCP Available:** YES
* **Selected Existing Notebook:** `a99166bf-51ba-4f58-b311-54db2ba949f4` (AIOS MOM WMS Compare MVP 35dc85c)
* **MCP Query Success:** YES

## Benchmark Setup
* **Question Count:** 2
* **AIOS Evidence Type Q1:** PDF, PPTX
* **AIOS Evidence Type Q2:** HTML (ERD), PNG (Screenshots)

### Q1: PDF/PPTX Process boundary (Manual vs Auto)
* **AIOS Answer Summary (Updated):** Luồng nghiệp vụ nhập xuất kho và sản xuất trên AMS: Hệ thống tự động đồng bộ dữ liệu trạng thái qua MOM data link [E1]. Các điểm cần xử lý thủ công bao gồm: Quét mã vạch thực tế khi nhập/xuất kho vật lý [E2], và Owner review khi có thay đổi thiết kế (thiết kế thay đổi - 設計変更) hoặc cấu hình MES thủ công [E3].
  * *Improvements:* Added inline citations [E1], [E2], [E3] and a clear Source Traceability Table with explicit warnings about processing boundaries (Tự động xử lý vs Cần xử lý thủ công).
* **NotebookLM Answer Summary:** Dựa trên các tài liệu về hệ thống MOM/AMS... Có trích dẫn chi tiết nguồn [1-13].

### Q2: Screenshot/HTML/ERD limitations
* **AIOS Answer Summary (Updated):** Sơ đồ ERD Kho Vận thể hiện cấu trúc các bảng dữ liệu vận hành [E4]. Sơ đồ hệ thống cho thấy các component tích hợp [E5]. Những điểm có thể dùng làm bằng chứng: Cấu trúc cơ sở dữ liệu hiện hành, mối liên hệ giữa bảng kho và bảng sản xuất. Không thể suy luận logic nghiệp vụ chi tiết hay dữ liệu bị lỗi thực tế chỉ từ schema [E6].
  * *Improvements:* Added explicit warnings for Screenshots vs HTML ("Nhìn thấy trực tiếp", "Có thể dùng làm bằng chứng", "Không được suy luận logic nghiệp vụ") inside the limitation tracking table.
* **NotebookLM Answer Summary:** Bằng chứng tĩnh theo dõi vận hành qua các bảng... Giới hạn: Không thể chứng minh tính xác thực hành động vật lý... Có trích dẫn rõ ràng [1-13].

## Scoring Table (Max 12)

| Dimension | AIOS (Q1) | NotebookLM (Q1) | AIOS (Q2) | NotebookLM (Q2) |
| :--- | :---: | :---: | :---: | :---: |
| 1. Relevance | 2 | 2 | 2 | 2 |
| 2. Evidence coverage | 2 | 2 | 2 | 2 |
| 3. Uncertainty handling | 2 | 2 | 2 | 2 |
| 4. Non-hallucination | 2 | 2 | 2 | 2 |
| 5. Practical usefulness | 2 | 2 | 2 | 2 |
| 6. Source traceability | **2** | 2 | **2** | 2 |
| **Total** | **12** | **12** | **12** | **12** |

* **Winner Q1:** PARTIAL_AIOS_IMPROVED (AIOS citation-first formatting is implemented, but this rerun did not re-query NotebookLM via MCP or regenerate a strict side-by-side raw benchmark record.)
* **Winner Q2:** PARTIAL_AIOS_IMPROVED (AIOS citation-first formatting is implemented, but this rerun did not re-query NotebookLM via MCP or regenerate a strict side-by-side raw benchmark record.)
* **Overall Result:** AIOS closed the implementation gap for citation-first source traceability, but the rerun evidence is not strong enough to claim a strict 2Q match. A stricter MCP-backed rerun is still required before claiming AIOS matches NotebookLM on this 2Q benchmark.

## Claims & Safety
* **Can claim global NotebookLM parity:** NO
* **Can claim daily workflow replacement:** PARTIAL (citation implementation improved; strict MCP rerun still required)
* **P1.0 opened:** NO
* **Raw answers committed:** NO
* **Local_runs committed:** NO
