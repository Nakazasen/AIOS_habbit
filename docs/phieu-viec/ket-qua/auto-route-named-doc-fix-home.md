# BÁO CÁO THỰC THI VÉ AUTO-ROUTE-NAMED-DOC-FIX-HOME

- **Mã vé:** `DESKTOP-AUTO-ROUTE-NAMED-DOC-FIX-HOME` (Ticket `AUTO-ROUTE-NAMED-DOC-FIX-HOME`)
- **Kho mã:** `AIOS_habbit`
- **Nhánh thực thi:** `phieu-viec/rag-fix1`
- **Mã commit đầy đủ:** `be6894870ec6d2d72725cd77b1f734e31ce7f38a`
- **Cấu hình thực thi:** Tuân thủ biên bản `BB-CONFIG-PARITY-01`, chế độ CPU-only, không can thiệp chỉ mục production.

---

## 1. Nguyên nhân gốc (Root Cause Analysis)

Qua chẩn đoán chu trình định tuyến ở chế độ Tự động (`forced_domain="auto"` hoặc `None`), phát hiện 2 nguyên nhân cốt lõi khiến câu hỏi *"Theo tài liệu Tab led cam ung.pdf (Touch Panel Specification), điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản (Storage) touch panel là bao nhiêu?"* bị sai lệch:

1. **Bộ định tuyến miền (`index_domain.detect_domain_from_question`):**
   - Chỉ tính điểm từ khóa cứng (`_score_text`) đối với 3 miền ban đầu (`lsu`, `dieu_tra_loi`, `mom`).
   - Hoàn toàn chưa có cơ chế kiểm tra xem câu hỏi có chứa tên một tài liệu cụ thể trong kho hay không.
   - Tài liệu `Tab led cam ung.pdf` thuộc khối `tong_hop` (Tổng hợp) và không chứa từ khóa LSU/MOM/Điều tra lỗi trong câu hỏi, dẫn tới tổng điểm bằng 0. Hệ thống rơi vào fallback mặc định `dieu_tra_loi` với confidence 0.0 và ghi nhận *"câu hỏi chưa rõ lĩnh vực; chọn khối khả dĩ nhất"*.

2. **Làn cấu trúc cướp quyền truy vấn (`try_structured_table_evidence`):**
   - Tại nhánh số 7 (Overview & Date Range) của `structured_query.py`, điều kiện kiểm tra tệp Spec là `elif "spec" in q_norm:`. Do cụm từ tiếng Anh `"Touch Panel Specification"` chứa chuỗi con `"spec"`, điều kiện này bị kích hoạt ngoài ý muốn.
   - Đồng thời, hàm `is_structured_file_in_domain` luôn trả về `True` khi `forced_domain` là `None` hoặc `"auto"`.
   - Hệ thống ngộ nhận câu hỏi đang truy vấn tệp `2026_08_Spec.csv` và trả về kết quả đếm bản ghi CSV, bỏ qua hoàn toàn nội dung tài liệu PDF được nêu đích danh.

---

## 2. Các điểm sửa đổi trong mã nguồn (Implementation Details)

### 2.1. `src/aios_habit/index_domain.py`
- Bổ sung các hàm nhận diện và bóc tách tài liệu đích danh:
  - `clean_named_doc_token(name)`: Làm sạch tiền tố tiếng Việt/tiếng Anh (`tài liệu`, `file`, `tệp`, `báo cáo`, `theo`...).
  - `extract_named_document_candidates(question)`: Trích xuất các ứng viên tên tệp có đuôi mở rộng (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.pptx`, `.txt`, `.msg`).
  - `match_named_documents(question, db_path, sources)`: Khớp trực tiếp với danh mục tài liệu trong thư viện `library.sqlite` và nguồn nạp vào. Trả về `(matched_specs, explicit_missing_doc_names)`.
- Cập nhật `detect_domain_from_question`:
  - Khi câu hỏi nêu đích danh tài liệu có thật trong kho: Neo trực tiếp vào khối tri thức chứa tài liệu đó (ví dụ `tong_hop` đối với `Tab led cam ung.pdf`) với độ tin cậy tuyệt đối `confidence = 1.0`.
  - Khi câu hỏi nêu đích danh tài liệu nhưng không tồn tại: Trả về trạng thái từ chối với `confidence = 0.0` và ghi rõ tài liệu bị thiếu.
- Cập nhật `get_specs_for_domain`: Khi câu hỏi nêu tài liệu cụ thể, tự động neo danh sách `allowed_set` đúng vào các `SourceSpec` của tài liệu đó, ngăn ngừa hiện tượng phân tán sự chú ý sang các tài liệu khác.

### 2.2. `src/aios_habit/rag_v2/structured_query.py`
- Bổ sung chốt chặn ở đầu hàm `try_structured_table_evidence`:
  - Nếu câu hỏi nêu đích danh tài liệu phi cấu trúc (ví dụ `.pdf`, `.docx`, `.msg`), làn cấu trúc lập tức trả về `None` để nhường quyền cho làn truy hồi tài liệu.
  - Nếu câu hỏi nêu đích danh tài liệu nhưng tài liệu không tồn tại trong kho, làn cấu trúc lập tức trả về `None`, không được cướp quyền để trả về thống kê CSV.
- Tại nhánh #7: Sửa biểu thức chính quy kiểm tra tệp `2026_08_Spec.csv` thành `re.search(r"\b2026_08_spec\b|\bspec\.csv\b|\bspecs?\b", q_norm) and not re.search(r"\bspecification\b", q_norm)` để không bao giờ bị kích hoạt bởi cụm từ `specification`.

### 2.3. `src/aios_habit/workspace_chat_rag_v2_adapter.py`
- Cập nhật `_select_domain_route`: Khi phát hiện câu hỏi nêu đích danh tài liệu (`is_named_doc = True`), tự động bật định tuyến miền sang khối tương ứng (`tong_hop`) ngay cả khi cờ định tuyến chung đang tắt.
- Trong `retrieve_workspace_chat_evidence`:
  - Kiểm tra `match_named_documents`. Nếu câu hỏi nêu tài liệu đích danh không tồn tại, trả về payload từ chối trung thực `status = "named_document_not_found"` kèm thông điệp: *"Chưa đủ bằng chứng trong kho tri thức: Không tìm thấy tài liệu '...' được nêu đích danh trong câu hỏi để tra cứu."*
  - Truyền `forced_domain = target_domain` vào `_try_structured_excel_evidence` để đảm bảo làn bảng tính tôn trọng miền đã định tuyến.

### 2.4. `src/aios_habit/workspace_chat_app.py`
- Tại hàm xử lý luồng QA `_run_chat_turn_async`:
  - Truyền `sources` vào `detect_domain_from_question`.
  - Khi nhận `status == "named_document_not_found"`, app lập tức trả về đáp án từ chối trung thực kèm huy hiệu `local_truthful_refusal` / `system_guard`, ngăn chặn hoàn toàn việc rơi vào cơ chế `deliver_draft_answer` (chống ảo giác).

---

## 3. Bằng chứng kiểm chứng hai chiều (Verification Evidence)

### 3.1. Kiểm chứng câu hỏi `Tab led cam ung.pdf` qua đường ống đầy đủ
Thực thi câu hỏi qua hàm `_run_chat_turn_async` với `forced_domain="auto"`:
```
[RETRIEVAL_MICRO_TIMING] collection=tong_hop pipe_wait_ms=0.00 coverage_verify_ms=0.78 lexical_ms=125.11 embed_ms=224.88 dense_ms=50.50 sparse_ms=10.58 fuse_ms=5.94 dense_resident=True dense_state=thuong_tru
```
- **Miền định tuyến:** `tong_hop` (Tổng hợp), `confidence: 1.0`, `applied: True`.
- **Làn cấu trúc:** Trả về `None` (không cướp quyền).
- **Trích đoạn thu thập:** 10 đoạn trích 100% đến từ tệp `Tab led cam ung.pdf`.
- **Dữ kiện trích xuất tại đoạn [4]:**
  - Điều kiện nhiệt độ bảo quản (Storage temp): `-30 ~ 70 °C` (Mục 5.4.3).
  - Điều kiện độ ẩm bảo quản (Storage humid): `10 ~ 90 %RH` (Mục 5.4.4).
  - Nhiệt độ bầu ướt tối đa: `38 °C`, không ngưng tụ.

### 3.2. Kiểm chứng câu hỏi nêu tài liệu không tồn tại trong kho
Thực thi câu hỏi *"Theo tài liệu khong_ton_tai_123.pdf, điều kiện nhiệt độ và độ ẩm tiêu chuẩn để bảo quản là bao nhiêu?"*:
- **Trạng thái:** `ok = True`, `status = "named_document_not_found"`.
- **Huy hiệu:** `{'provider': 'local_truthful_refusal', 'ai_source': 'system_guard', 'document_missing': True}`.
- **Nội dung trả lời:** *"Chưa đủ bằng chứng trong kho tri thức: Không tìm thấy tài liệu "khong_ton_tai_123.pdf" được nêu đích danh trong câu hỏi để tra cứu."*
- Hoàn toàn từ chối trung thực, không bị cướp quyền bởi CSV hay suy diễn sai.

### 3.3. Kiểm chứng 6 câu đích của làn cấu trúc (`rows-csv-structured-lane-fix-targets.jsonl`)
Chạy kiểm tra lại toàn bộ 6 câu mục tiêu:
1. `Q0849`: *"File có bao nhiêu record lỗi và phạm vi ngày nào?"* -> Nguồn: `2026_08_Error_BowOverAdjust.csv` [PASS]
2. `Q0850`: *"Yellow、Cyan、Magenta分别有多少件？"* -> Nguồn: `2026_08_Error_BowOverAdjust.csv` [PASS]
3. `Q1034`: *"哪一天Error Record最多？"* -> Nguồn: `2026_08_Error.csv` [PASS]
4. `Q0824`: *"`61C1068E7022`は8月12日と13日で判定Patternが変わりましたか。"* -> Nguồn: `2026_08_UnitTest.csv` [PASS]
5. `Q0668`: *"g1 và g2 có nominal và giới hạn nào?"* -> Nguồn: `3V2ND19040-MOUNT LD BLOCK  LOT 18.8.2026.xlsx` [PASS]
6. `Q0843`: *"Cặp giới hạn Current phổ biến nhất là bao nhiêu?"* -> Nguồn: `2026_08_Spec.csv` [PASS]
-> **Kết quả: 6/6 câu đạt điểm tuyệt đối 18/18.**

---

## 4. Bốn cổng chất lượng của repository (4 Quality Gates)

1. **Gate 1 - Compileall:**
   ```powershell
   python -m compileall src tests
   ```
   *Kết quả:* Exit code 0, không có lỗi cú pháp.

2. **Gate 2 - Pytest các bộ test liên quan:**
   ```powershell
   pytest tests/test_block_pin_lane_precedence.py tests/test_index_domain.py tests/test_rag_v2_structured_query.py tests/test_workspace_chat_knowledge_block.py tests/test_block_selector_tonghop_regression.py -v
   ```
   *Kết quả:* **96/96 tests PASSED** trong 2.59s.

3. **Gate 3 - CLI Audit:**
   ```powershell
   python -m aios_habit.cli audit
   ```
   *Kết quả:* `{"errors": [], "status": "PASS", "warnings": []}`.

4. **Gate 4 - Import sanity check:**
   ```powershell
   python -c "import aios_habit.workspace_chat_app; print('GATE 4 IMPORT SUCCESS')"
   ```
   *Kết quả:* `GATE 4 IMPORT SUCCESS`.
