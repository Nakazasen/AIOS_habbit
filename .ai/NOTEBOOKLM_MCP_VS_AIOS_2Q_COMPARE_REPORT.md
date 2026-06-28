# NotebookLM MCP vs AIOS 2Q Compare Report

* **Branch:** main
* **HEAD:** 71efbd5
* **NotebookLM MCP Available:** YES
* **Selected Existing Notebook:** `a99166bf-51ba-4f58-b311-54db2ba949f4` (AIOS MOM WMS Compare MVP 35dc85c)
* **MCP Query Success:** YES

## Benchmark Setup
* **Question Count:** 2
* **AIOS Evidence Type Q1:** PDF, PPTX
* **AIOS Evidence Type Q2:** HTML (ERD), PNG (Screenshots)

### Q1: PDF/PPTX Process boundary (Manual vs Auto)
* **AIOS Answer Summary:** Luồng nghiệp vụ nhập xuất kho và sản xuất trên AMS: Hệ thống tự động đồng bộ dữ liệu trạng thái qua MOM data link. Các điểm cần xử lý thủ công bao gồm: Quét mã vạch thực tế khi nhập/xuất kho vật lý, và Owner review khi có thay đổi thiết kế (thiết kế thay đổi - 設計変更) hoặc cấu hình MES thủ công.
* **NotebookLM Answer Summary:** Dựa trên các tài liệu về hệ thống MOM/AMS, các luồng nghiệp vụ chính được thiết kế với sự phân chia: 1. Quản lý Thay đổi Thiết kế (Review thủ công từ QA). 2. Nhập/Xuất kho (Quét mã HT thủ công, Oricon Gate tự động cập nhật MOM). 3. Sự cố dây chuyền (Tạo đơn sửa chữa bằng HT, QC/IE phê duyệt thủ công). 4. Điều hướng AGV (Tự động kích hoạt qua Matecon). Có trích dẫn chi tiết nguồn [1-13].

### Q2: Screenshot/HTML/ERD limitations
* **AIOS Answer Summary:** Sơ đồ ERD Kho Vận thể hiện cấu trúc các bảng dữ liệu vận hành. Sơ đồ hệ thống cho thấy các component tích hợp. Những điểm có thể dùng làm bằng chứng: Cấu trúc cơ sở dữ liệu hiện hành, mối liên hệ giữa bảng kho và bảng sản xuất. Không thể suy luận logic nghiệp vụ chi tiết hay dữ liệu bị lỗi thực tế chỉ từ schema.
* **NotebookLM Answer Summary:** Bằng chứng tĩnh theo dõi vận hành qua các bảng như `T_PARTS_RECEIVE` (nhập kho), `T_PARTS_OUT` (xuất kho), `StatusCodeLinkage_Ver00` (dừng máy). Trạng thái `HOUSE_FINISH_FLG` chứng minh cất hàng. Giới hạn: Không thể chứng minh tính xác thực hành động vật lý (hàng có thực sự vào kho hay không), không xác nhận được người thực sự bấm nút (chỉ chứng minh tài khoản), không tìm được root cause của độ trễ (latency) chỉ từ timestamp. Có trích dẫn rõ ràng [1-13].

## Scoring Table (Max 12)

| Dimension | AIOS (Q1) | NotebookLM (Q1) | AIOS (Q2) | NotebookLM (Q2) |
| :--- | :---: | :---: | :---: | :---: |
| 1. Relevance | 2 | 2 | 2 | 2 |
| 2. Evidence coverage | 2 | 2 | 2 | 2 |
| 3. Uncertainty handling | 2 | 2 | 2 | 2 |
| 4. Non-hallucination | 2 | 2 | 2 | 2 |
| 5. Practical usefulness | 2 | 2 | 2 | 2 |
| 6. Source traceability | 1 | 2 | 1 | 2 |
| **Total** | **11** | **12** | **11** | **12** |

* **Winner Q1:** NotebookLM_WIN (Better source traceability)
* **Winner Q2:** NotebookLM_WIN (Better source traceability and detailed deep-dive into table names)
* **Overall Result:** AIOS ties closely with NotebookLM on factual understanding, but NotebookLM is slightly stronger due to native inline citations and deeper detailed extraction of specific database table columns from screenshots. 

## Claims & Safety
* **Can claim global NotebookLM parity:** NO
* **Can claim daily workflow replacement:** PARTIAL (For this 2Q tested document set only)
* **P1.0 opened:** NO
* **Raw answers committed:** NO
* **Local_runs committed:** NO
