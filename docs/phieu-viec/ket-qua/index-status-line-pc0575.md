# Báo cáo vé INDEX-STATUS-LINE-PC0575 — Dòng trạng thái chỉ mục trong khung chat

- Mã vé: `INDEX-STATUS-LINE-PC0575`
- Máy thực hiện: công ty KDTVN-PC0575 (thợ agy — Antigravity CLI)
- Thời gian thực hiện: 2026-10-07 21:15 → 21:30 +07
- Báo cáo: `docs/phieu-viec/ket-qua/index-status-line-pc0575.md`
- Trạng thái nghiệm thu đề xuất: **ĐẠT**

---

## 1. Mục tiêu & Yêu cầu của vé

1. **Hiển thị thông tin chỉ mục thực tế:** Thêm đúng 1 dòng trạng thái mảnh (`caption`, chữ nhỏ/mờ) trong khung chat của `src/aios_habit/workspace_chat_app.py`, đặt ngay trên vùng hội thoại (`chat_container`). Không thêm ô chọn, không thêm nút bấm, không thêm menu/sidebar.
2. **Nội dung dòng trạng thái:** Lấy trực tiếp từ chính tệp chỉ mục mà ứng dụng đang nạp:
   - Tên tệp chỉ mục (vd: `library.sqlite`).
   - Số lượng tài liệu và số lượng mảnh đếm trực tiếp từ SQLite DB đang mở (kỳ vọng trên máy công ty: 889 tài liệu / 149.800 mảnh).
   - Mã nhận diện rút gọn: 12 ký tự hex đầu của **vân tay logic**: SHA-256 trên danh sách sắp xếp của `mã tài liệu | vân tay nội dung | số mảnh` (thước chuẩn điều phối chốt tại `SRC-SYNC` thay cho MD5 thô của SQLite).
   - Tên backend đang dùng (vd: `ONNX fp32`).
   - Mẫu định dạng: `Kho đang dùng: library.sqlite · 889 tài liệu · 149.800 mảnh · mã 87a3626a85bc · ONNX fp32`.
3. **Xử lý trạng thái lỗi rõ ràng:** Khi tệp chỉ mục thiếu hoặc không đọc được, hiển thị cảnh báo `⚠ Không nạp được kho tri thức`. Tuyệt đối không để trống im lặng hoặc dùng số liệu cũ từ phiên trước.
4. **Hiệu năng & bộ nhớ đệm (Caching):** Số liệu được tính toán một lần khi ứng dụng nạp chỉ mục và được lưu trong bộ nhớ đệm của phiên làm việc (`session_state`), không tính lại mỗi khi người dùng gửi câu hỏi.
5. **Rào cứng tuân thủ:**
   - CHỈ hiển thị: không đổi logic app chọn chỉ mục, không đụng logic retrieval/synthesis, không ghi/sửa index.
   - Tương thích Python 3.11.
   - Không merge `main`.

---

## 2. Kết quả đối chiếu thực tế trên máy công ty PC0575

### 2.1. Truy vấn cơ sở dữ liệu độc lập (kiểm chứng chỉ-đọc `mode=ro`)

- Tệp chỉ mục đang dùng: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
- Kích thước tệp: 2.853.646.336 byte (~2,85 GB)
- Truy vấn độc lập:
  - `PRAGMA quick_check`: `ok`
  - Đếm số tài liệu: `SELECT COUNT(DISTINCT document_id) FROM chunks` → **889** tài liệu
  - Đếm số mảnh: `SELECT COUNT(*) FROM chunks` → **149.800** mảnh (385 mảnh tóm tắt `document_summary` + 149.415 mảnh nội dung)
  - Số tài liệu mang vân tay nội dung: 540 mã có vân tay + 348 mã trống (gpu-...) + 1 mã chỉ tóm tắt (tổng 889)

### 2.2. Tính toán vân tay logic độc lập (Chuẩn SRC-SYNC / INDEX-VERIFY)

- Công thức: Với mỗi mã tài liệu, tạo một dòng `mã|vân tay nội dung|số mảnh nội dung`, sắp xếp theo mã, nối bằng ký tự xuống dòng `\n` (không thừa dòng cuối), băm SHA-256.
- Kết quả SHA-256 đầy đủ:
  `87a3626a85bc32c81ec899c0b5c47d59f6208afd73c80cc94c0a4f2f1df6de3c`
  *(Khớp 100% mốc SRC-SYNC của máy công ty và mốc INDEX-VERIFY của máy nhà)*
- Mã nhận diện rút gọn 12 ký tự hex đầu: **`87a3626a85bc`**

### 2.3. Dòng trạng thái hiển thị thực tế trên giao diện app

```text
Kho đang dùng: library.sqlite · 889 tài liệu · 149.800 mảnh · mã 87a3626a85bc · ONNX fp32
```

### 2.4. Bảng đối chiếu số liệu

| Thành phần hiển thị | Số đọc trực tiếp từ DB | Kết quả app hiển thị | Đối chiếu |
|---|---|---|---|
| **Tên tệp chỉ mục** | `library.sqlite` | `library.sqlite` | **Khớp 100%** |
| **Số tài liệu** | 889 | 889 tài liệu | **Khớp 100%** |
| **Số mảnh** | 149.800 | 149.800 mảnh | **Khớp 100%** |
| **Mã 12-hex logic** | `87a3626a85bc` | `87a3626a85bc` | **Khớp 100%** |
| **Backend** | ONNX fp32 | ONNX fp32 | **Khớp 100%** |
| **Khi thiếu/lỗi DB** | DB thiếu / DB hỏng | `⚠ Không nạp được kho tri thức` | **Khớp 100%** |

---

## 3. Kiến trúc giải pháp kỹ thuật

1. **Module `src/aios_habit/index_status.py`:**
   - `get_index_status_info(db_path, backend_name)`: Đọc DB chỉ-đọc (`mode=ro`), đếm chunks, đếm docs, tính vân tay logic 12-hex, trả về `IndexStatusInfo`. Bắt mọi ngoại lệ và trả về `status_line="⚠ Không nạp được kho tri thức"` nếu có sự cố.
   - `get_cached_index_status_line(db_path, backend_name, session_state)`: Lưu trữ kết quả tính toán vào `session_state["wsc_index_status_cache"]`, đảm bảo chỉ tính 1 lần duy nhất trong phiên làm việc.
   - `resolve_active_index_db_path(collection_id)`: Xác định chính xác tệp SQLite mà app đang nạp dựa trên cấu hình môi trường và `collection_runtime_layout`.
   - `format_thousands_vi(value)`: Định dạng số hàng nghìn bằng dấu chấm (`149.800`).
   - `resolve_display_backend_name()`: Ánh xạ chuẩn `onnx` → `ONNX fp32`, `onnx_int8` → `ONNX int8`, `pytorch` → `PyTorch`.

2. **Tích hợp trong `src/aios_habit/workspace_chat_app.py`:**
   - Thêm dòng trạng thái mảnh bằng `st.caption(_idx_status_text)` ngay trên vùng hội thoại (`chat_container`), trước danh sách tin nhắn.
   - Đúng 1 dòng caption mỏng, không nút bấm, không menu, không phá vỡ giao diện.

---

## 4. Kiểm chứng các cổng chất lượng (AGENTS.md)

1. **Cổng 1 — Biên dịch mã nguồn (`compileall`):**
   - Lệnh: `python -m compileall src tests`
   - Kết quả: **PASS** (0 lỗi biên dịch trên toàn bộ cây `src/` và `tests/`).
2. **Cổng 2 — Unit test hồi quy & kiểm thử chức năng:**
   - Lệnh: `pytest tests/test_index_status.py -v`
   - Kết quả: **9/9 test PASS** (100%):
     - `test_index_status_missing_file`: PASS (bắt lỗi khi tệp không tồn tại).
     - `test_index_status_none_path`: PASS (bắt lỗi khi đường dẫn rỗng).
     - `test_index_status_empty_db`: PASS (bắt lỗi khi DB rỗng không có bảng).
     - `test_index_status_no_chunks`: PASS (bắt lỗi khi bảng chunks rỗng).
     - `test_index_status_mock_db_counts_and_fingerprint`: PASS (kiểm tra tính toán số đếm và vân tay trên mock DB).
     - `test_index_status_thousand_formatting`: PASS (kiểm tra định dạng `.` hàng nghìn tiếng Việt).
     - `test_index_status_caching`: PASS (kiểm tra tính đúng đắn của cơ chế cache trong session state).
     - `test_resolve_display_backend_name`: PASS (kiểm tra tên hiển thị backend).
     - `test_index_status_matches_real_db_if_present`: PASS (khẳng định số hiển thị khớp số đọc trực tiếp từ DB thật).
3. **Cổng 3 — Kiểm tra tuân thủ kiến trúc (`cli audit`):**
   - Lệnh: `python -m aios_habit.cli audit`
   - Kết quả: **`"status": "PASS"`**, 0 errors, 0 warnings.
4. **Cổng 4 — Kiểm tra nhập module app (`import workspace_chat_app`):**
   - Lệnh: `python -c "import aios_habit.workspace_chat_app; print('workspace_chat_app import OK')"`
   - Kết quả: **PASS** (`workspace_chat_app import OK`).

---

## 5. Kết luận

Vé `INDEX-STATUS-LINE-PC0575` đã được hoàn thành trọn vẹn, đáp ứng chính xác mọi yêu cầu trong prompt và quy ước mailbox:
- Dòng trạng thái chỉ mục mảnh đã hiển thị đúng vị trí trong khung chat.
- Số liệu đếm trực tiếp và mã vân tay logic 12-hex khớp 100% với cơ sở dữ liệu thật.
- Có cơ chế cảnh báo lỗi và cache theo phiên.
- Vượt qua đầy đủ 4 cổng chất lượng của repository.
- Sẵn sàng bàn giao cho điều phối Muse nghiệm thu (`xong-cho-duyet`).
