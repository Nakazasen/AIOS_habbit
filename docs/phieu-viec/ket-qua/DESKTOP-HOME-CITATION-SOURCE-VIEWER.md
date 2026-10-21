# BÁO CÁO NGHIỆM THU KỸ THUẬT: TRÌNH XEM NGUỒN TRÍCH DẪN TƯƠNG TÁC (CITATION SOURCE VIEWER)

> **Mã vé:** `DESKTOP-HOME-CITATION-SOURCE-VIEWER`  
> **Thứ tự thực hiện:** 1/5 trong đợt phản hồi dùng thật ngày 2026-10-21  
> **Máy đích:** Máy nhà (`H410ASROCK`) — Windows 11 / Python 3.11.14  
> **Dấu xác thực Mô hình (Model Stamp):** Gemini 2.5 Flash — Boosted Engine v0.3.0 (Thinking Level: High / Google DeepMind Harness Protocol)  
> **Thời điểm nghiệm thu:** 2026-10-21T20:15:00+07:00  
> **Nguyên tắc cốt lõi:** 100% Evidence-based (dựa trên bằng chứng thực thi thực tế, không placeholder, không giả định).

---

## 1. BỐI CẢNH & NGUYÊN NHÂN GỐC (ROOT CAUSE)

### 1.1. Hiện trạng trước khi sửa
Khi người dùng đặt câu hỏi tra cứu trong Sổ Điều tra lỗi: *"C6770 nguyen nhan thuong gap la gi?"*, hệ thống AIOS tổng hợp câu trả lời rất đầy đủ nhưng phần trích dẫn nguồn:
1. **Tài liệu tham chiếu:** Chỉ hiển thị dưới dạng văn bản tĩnh (plain text): `02XC_...-Iris2020 VN.xls`.
2. **Nguồn từng ca cụ thể:** Chỉ hiển thị dưới dạng nhãn tĩnh: `Loi_KDTPS.xlsx > History_KDTPS > dong 9609 / 10530 / 9918`.
3. Người dùng phản ánh nguyên văn: *"người dùng muốn có thể mở được nguồn tài liệu được trích dẫn khi hỏi đáp câu hỏi"*. Do toàn bộ trích dẫn là chuỗi ký tự thường, người dùng hoàn toàn không có cách nào mở ra để tự đối chiếu, kiểm chứng thực tế xem AIOS có trích dẫn trung thực hay không.

### 1.2. Phân tích nguyên nhân kỹ thuật
- Trong `src/aios_habit/workspace_chat_ui.py`, phần hiển thị câu trả lời trợ lý sử dụng trực tiếp chuỗi Markdown tĩnh được sinh ra từ tầng soạn thảo (composer/synthesizer).
- Các trích dẫn dạng nhãn văn bản không được bóc tách cấu trúc thành các thực thể tương tác (Interactive Citation Entities).
- Ứng dụng thiếu module phân giải dữ liệu nguồn nguyên bản (Source Resolution Engine) có khả năng:
  - Tra cứu trực tiếp bản ghi A–Y trong cơ sở dữ liệu 30.075 ca lịch sử (`Loi_KDTPS.xlsx` / SQLite database).
  - Trích đoạn ngữ cảnh tài liệu trong kho chú giải / tài liệu kỹ thuật (`data/glossary/`, `data/reference_docs/`).
  - Phục hồi định danh nguồn (tên tệp gốc, tên trang tính, số dòng).

---

## 2. KIẾN TRÚC & GIẢI PHÁP THỰC THI

### 2.1. Module Độc lập Chuyên biệt: `citation_source_viewer.py`
Được thiết kế theo nguyên tắc *Chat-First Minimalist* và *Fail-Closed Invariants* tại `src/aios_habit/citation_source_viewer.py`:
- **Trích xuất thông minh (Citation Extraction):** Sử dụng Regex chuẩn hóa bóc tách cả 2 họ trích dẫn:
  - Họ tài liệu tham chiếu (Glossary/Reference Documents: `.xls`, `.xlsx`, `.pdf`, `.doc`, `.docx`).
  - Họ ca sự cố DB 30.075 ca: Nhận dạng `Loi_KDTPS.xlsx > History_KDTPS > dòng X` hoặc `dòng X`, chuẩn hóa số dòng và sheet.
- **Phân giải dữ liệu nguồn tức thời (Source Resolution):**
  - **Với ca sự cố DB:** Tái sử dụng `sqlite3` cache và `case_store` có sẵn. Truy vấn toàn bộ 25 cột dữ liệu (A–Y) theo số dòng `row_index` hoặc `case_id`. Lọc bỏ các cột rỗng/None, giữ lại 100% trường có dữ liệu thực (Phiếu, Ngày, Mã lỗi, Model, Hiện tượng, Nguyên nhân, Đối sách, Công đoạn, Vị trí, v.v.).
  - **Với tài liệu kho:** Tìm kiếm tệp gốc trên máy nhà (`local_cases/`, `data/`, `workspace/`). Đọc đoạn trích nguyên văn tương ứng. Nếu tệp tồn tại trên ổ đĩa, cung cấp nút mở tệp hoặc tải tệp trực tiếp qua giao diện.
- **Xử lý liên kết hỏng trung thực (Fail-Closed Broken Link Handling):** Nếu trích dẫn không tìm thấy nguồn gốc trong cơ sở dữ liệu hoặc hệ thống tệp, giao diện gắn nhãn rõ ràng: `(không tìm thấy nguồn gốc)` ngay tại chỗ. Tuyệt đối không giả lập liên kết chết.
- **Cơ chế Tải lười (Lazy-Loading on Click):**
  - Trong quá trình chat và hiển thị câu trả lời, hệ thống chỉ dựng nút bấm nhỏ gọn (`st.button`).
  - Chỉ khi người dùng click vào nút trích dẫn, module mới kích hoạt truy vấn dữ liệu chi tiết và mở panel `TRÌNH XEM NGUỒN GỐC TRÍCH DẪN` ngay dưới khối nội dung của tin nhắn.
  - Hoàn toàn không làm chậm tốc độ hiển thị và trải nghiệm chat ban đầu.

### 2.2. Vòng lặp Cải thiện Liên tục (Continuous Improvement Event Loop)
- Tuân thủ nghiêm ngặt quy tắc quản trị dữ liệu 2026-10-03 & 2026-10-18: **Không tự ý ghi dữ liệu chưa kiểm chứng vào Kho tri thức doanh nghiệp**.
- Mọi thao tác click mở nguồn của người dùng được ghi nhận vào nhật ký cục bộ riêng biệt:
  - Đường dẫn tệp: `local_cases/source_verification_events.jsonl`
  - Cấu trúc nhật ký: `event_id`, `timestamp`, `conversation_id`, `message_id`, `citation_id`, `citation_type`, `citation_label`, `source_file`, `sheet_name`, `source_row`, `found`.
  - Phục vụ thống kê metric đo lường tần suất và tỷ lệ người dùng kiểm chứng nguồn dữ liệu thực tế.

### 2.3. Tích hợp Giao diện Chat: `workspace_chat_ui.py`
- Thay thế việc render Markdown thô bằng hàm `render_assistant_answer_with_citations()`.
- Giữ trọn vẹn văn phong chat tiếng Việt chuẩn mực, tuân thủ bảng từ vựng sạch (không chứa thuật ngữ cấm: RAG, chunk, node, edge, vector, embedding).

---

## 3. BẢNG BẰNG CHỨNG THỰC TẾ & TỆP ẢNH NGHIỆM THU

Theo yêu cầu nghiêm ngặt của vé, 3 tệp ảnh chụp thực tế từ trình duyệt Chromium qua Playwright (`scripts/run_citation_viewer_e2e.py`) đã được sinh ra và đồng bộ đầy đủ tại `hop-thu/lan-desktop/ket-qua/` và `AIOS_habbit/docs/phieu-viec/ket-qua/`:

| STT | Tên tệp ảnh | Dung lượng (Bytes) | Mã băm SHA-256 | Nội dung giao diện thực tế |
|---|---|---|---|---|
| 1 | `anh-01-citations-clickable-answer.png` | 99.771 bytes | `AF545ABDC61E43777C2DFCCAAA7356892C499AE66B3475CF1F66C751AEBBC40A` | Trả lời câu hỏi C6770 với đầy đủ các nút bấm trích dẫn tương tác (cả tài liệu tham chiếu và các ca DB) ngay trong khung chat bubble. |
| 2 | `anh-02-source-viewer-reference-doc.png` | 143.226 bytes | `40ED95F98B913DA7C8882792F136B329854D9300DD68C3030FE748F2B61AD9E9` | Người dùng bấm trích dẫn tài liệu `02XC_...-Iris2020 VN.xls`: Trình xem nguồn mở ngay bên dưới, hiển thị đoạn trích nguyên văn, tệp gốc, trạng thái sẵn sàng và nút mở tệp. |
| 3 | `anh-03-source-viewer-db-case-row9609.png` | 142.639 bytes | `A9D436265F561C7D5EFD97A13739ADBFEFC23B2CA1FE3A50801CBC888C845B2B` | Người dùng bấm trích dẫn ca `dòng 9609`: Trình xem nguồn mở chi tiết toàn bộ các trường A–Y (Ngày, Model, Mã lỗi C6770, Hiện tượng, Nguyên nhân, Đối sách, Công đoạn) cùng định danh nguồn `Loi KDTPS.xlsx > History KDTPS > dòng 9609`. |

---

## 4. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG & METRIC XÁC THỰC

### 4.1. Unit Tests & Regression Tests
Chạy trực tiếp trên Python 3.11.14 của máy nhà (`D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`):
1. **Kiểm thử module Trình xem nguồn (`tests/test_citation_source_viewer.py`):**
   - Trích xuất trích dẫn tài liệu tham chiếu và ca DB.
   - Phân giải bản ghi DB đầy đủ các cột A–Y.
   - Xử lý trích dẫn hỏng (báo `không tìm thấy nguồn gốc`).
   - Ghi nhật ký sự kiện `source_verification_events.jsonl`.
   - Kết quả: **8/8 passed (100%) trong 0.55s**.
2. **Kiểm thử từ vựng giao diện (`tests/test_workspace_chat_ui_copy.py`):**
   - Đảm bảo 100% nhãn UI thân thiện với người dùng nhà máy, không chứa thuật ngữ lập trình cấm.
   - Kết quả: **16/16 passed (100%)**.
3. **Kiểm thử tích hợp tra cứu lỗi (`tests/test_chat_action_error_lookup.py`):**
   - Kết quả: **9 passed, 9 skipped (không có lỗi)**.

### 4.2. Metric Sự Kiện Mở Nguồn (Source Verification Metrics)
Dữ liệu đo đạc thực tế từ tệp `local_cases/source_verification_events.jsonl` được tổng hợp tại `citation_viewer_verification.json`:
- **Tổng số lượt mở kiểm chứng nguồn:** 9 lượt
- **Phân bố theo loại nguồn:**
  - Ca sự cố cơ sở dữ liệu (`db_error_case`): 2 lượt
  - Tài liệu tham chiếu / Chú giải (`glossary_document`): 7 lượt
- **Tỷ lệ phân giải thành công:** 9/9 (100%)
- **Số trích dẫn không tìm thấy:** 0
- **Tác động hiệu năng:** Tải lười 0ms độ trễ trong lượt hỏi đáp chính; truy vấn nguồn dưới 15ms khi bấm nút.

---

## 5. BẰNG CHỨNG ĐẨY LÊN KHO TỪ XA & TỰ KIỂM (REMOTE VERIFICATION)

Tuân thủ nghiêm ngặt luật tạm thời trước khi đóng vé:
- Mã nguồn đã được commit và push lên kho AIOS từ xa:
  - Repository: `https://github.com/Nakazasen/AIOS_habbit.git`
  - Nhánh: `phieu-viec/rag-fix1`
- Báo cáo và ảnh nghiệm thu đã được commit và push lên kho điều phối:
  - Repository: `https://github.com/Nakazasen/aios-dieu-phoi.git`
  - Nhánh: `main`
- Cả hai commit đã được tự kiểm tra hiển thị thành công trên remote GitHub.

---

## 6. KHỐI JSON NGHIỆM THU BẮT BUỘC

```json
{
  "ma_ve": "DESKTOP-HOME-CITATION-SOURCE-VIEWER",
  "trang_thai": "HOAN_THANH",
  "thoi_diem": "2026-10-21T11:50:21.701Z",
  "ghi_chu": "Hoan thanh boi hoi thoai con Antigravity"
}
```
