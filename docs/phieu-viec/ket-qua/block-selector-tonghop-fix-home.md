# BÁO CÁO THỰC THI VÉ BLOCK-SELECTOR-TONGHOP-FIX-HOME
(Mã làn Desktop: `DESKTOP-BLOCK-SELECTOR-TONGHOP-FIX-HOME`)

- **Ngày thực hiện:** 2026-10-12
- **Môi trường thực thi:** Máy nhà (`May nha - h410asrock`) theo biên bản chuẩn `BB-CONFIG-PARITY-01`.
- **Cấu hình hiệu lực:** CPU Intel Core i3-10100 (4 cores / 8 threads), RAM 16 GB, chế độ thực thi CPU-only (`KMP_DUPLICATE_LIB_OK=TRUE`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`), Python 3.13.14.
- **Tuyến tổng hợp AI hiệu lực:** `nakazasen_router` / fallback cục bộ `local_grounded_fallback` (không dùng C-Agent theo luật phân định máy nhà).
- **Chỉ mục:** Kho hợp nhất production 894 tài liệu / 181.511 mảnh (`library.sqlite` trong `tri_thuc`), không sửa đổi hay ghi đè chỉ mục production.

---

## 1. Điểm dựng danh sách lựa chọn & Nguyên nhân thiếu `tong_hop`

### 1.1. Lớp giao diện (UI Selector):
- **Điểm dựng danh sách:** Hàm nội bộ trong khung soạn thảo tại `src/aios_habit/workspace_chat_app.py` (trước đây ở dòng ~4783).
- **Nguyên nhân thiếu:** Danh sách từ điển `block_choices` bị gán cứng chỉ gồm 3 khối chuyên sâu (`_DOMAIN_LSU`, `_DOMAIN_DIEU_TRA_LOI`, `_DOMAIN_MOM`) cùng lựa chọn `"auto"`. Khối `tong_hop` (72 tài liệu trong `domain_document_map.json`) bị bỏ sót do quyết định thiết kế cũ (Round 5) từng chặn khối này. Đồng thời, vòng lặp dựng các nút bấm popover chỉ lặp qua `("auto", *_DOMAINS)` nên người dùng không có nút chọn khối Tổng hợp.

### 1.2. Lớp Adapter (RAG V2 Adapter):
- **Điểm chặn:** Hàm `_select_domain_route` tại `src/aios_habit/workspace_chat_rag_v2_adapter.py` (trước đây ở dòng ~3404).
- **Nguyên nhân thiếu:** Danh sách trắng (whitelist) kiểm tra `forced_domain` chỉ so khớp với `index_domain.DOMAINS` (vốn chỉ gồm 3 domain `lsu`, `dieu_tra_loi`, `mom` cho bộ phân loại keyword). Khi nhận `forced_domain="tong_hop"`, adapter lập tức trả về `None`, khiến truy hồi không thể vào được khối Tổng hợp dù UI có gửi tín hiệu. Ngoài ra hàm `workspace_chat_domain_block_status()` ở sidebar cũng chỉ lặp qua `DOMAINS` nên không phản ánh trạng thái khối Tổng hợp.

---

## 2. Chi tiết điểm sửa đổi (Hai lớp)

### 2.1. Lớp định nghĩa miền & chuẩn hóa khối (`src/aios_habit/index_domain.py` & `src/aios_habit/i18n.py`):
1. **Bổ sung hằng số & tuple khối tri thức:**
   - Định nghĩa `DOMAIN_TONG_HOP = "tong_hop"`.
   - Giữ nguyên `DOMAINS = (DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM)` để bảo toàn 100% logic phân loại câu hỏi (taxonomy detection) và các test hồi quy hiện hữu.
   - Thêm bộ khối tri thức hoàn chỉnh: `KNOWLEDGE_BLOCKS = (DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM, DOMAIN_TONG_HOP)`.
   - Cập nhật `DOMAIN_DISPLAY[DOMAIN_TONG_HOP] = "Tổng hợp"` và `DOMAIN_COLLECTION_IDS[DOMAIN_TONG_HOP] = "tong_hop"`.
2. **Cập nhật đếm động tài liệu:**
   - Trong `get_domain_counts()`: khởi tạo `DOMAIN_TONG_HOP: 0`, cho kết quả đếm động chính xác:
     - `auto`: 894 tài liệu
     - `lsu`: 99 tài liệu
     - `dieu_tra_loi`: 679 tài liệu
     - `mom`: 44 tài liệu
     - `tong_hop`: 72 tài liệu
   - Trong `get_domain_document_ids()`: duyệt qua `KNOWLEDGE_BLOCKS`, trả về đúng 72 document IDs cho `tong_hop`.
3. **Đa ngữ i18n (`src/aios_habit/i18n.py`):**
   - Tiếng Việt: `"knowledge_block_tong_hop": "Tổng hợp"`
   - Tiếng Nhật: `"knowledge_block_tong_hop": "総合"`
   - Tiếng Trung: `"knowledge_block_tong_hop": "综合"`

### 2.2. Lớp giao diện (`src/aios_habit/workspace_chat_app.py`):
1. **Hàm module-level chuẩn hóa `get_workspace_chat_block_choices(locale: str = "vi")`:**
   - Tự động lấy số lượng tài liệu động từ `get_domain_counts()`.
   - Đảm bảo thứ tự chuẩn: `"auto"`, `"lsu"`, `"dieu_tra_loi"`, `"mom"`, `"tong_hop"`.
   - Cơ chế tương thích tiến: tự động quét `load_domain_document_map()` để bổ sung bất kỳ khối mới nào trong tương lai.
2. **Đồng bộ hóa bộ chọn Popover trong khung soạn thảo:**
   - Lặp qua `block_choices.keys()` thay vì hardcoded tuple cũ.
   - Khi chọn nút "Tổng hợp (72 tài liệu)", `st.session_state[knowledge_block_key]` nhận giá trị `"tong_hop"`.
3. **Sidebar Shared Blocks Expander:**
   - Bổ sung `"tong_hop": "knowledge_block_tong_hop"` vào `_shared_block_label_keys`.

### 2.3. Lớp Adapter RAG V2 (`src/aios_habit/workspace_chat_rag_v2_adapter.py`):
1. **Mở rộng whitelist trong `_select_domain_route`:**
   - Cho phép toàn bộ `index_domain.KNOWLEDGE_BLOCKS` (bao gồm `tong_hop`).
   - Route `tong_hop` được công nhận là `DomainRoute(applied=True, domain="tong_hop")` và chuyển tiếp chính xác 72 specs của khối Tổng hợp vào retrieval pipeline.
2. **Cập nhật `workspace_chat_domain_block_status`:**
   - Quét qua `KNOWLEDGE_BLOCKS`, báo cáo đầy đủ trạng thái cả 4 khối ở sidebar (`tong_hop` đạt trạng thái `ready: True`, 36.081.664 byte).

---

## 3. Test hồi quy bảo đảm chất lượng

### 3.1. Cập nhật test hiện hữu (`tests/test_index_domain.py`):
- Thay thế test cũ `test_forced_block_never_selects_tong_hop` (từ Round 5) thành `test_forced_block_selects_tong_hop` khẳng định adapter chấp nhận `tong_hop` với `applied=True`, `confidence=1.0`.
- Thêm test `test_forced_block_unknown_domain_returns_none` xác nhận whitelist vẫn chặn các khối lạ.

### 3.2. Bộ test hồi quy chuyên biệt (`tests/test_block_selector_tonghop_regression.py`):
Bao gồm 9 test cases kiểm chứng chặt chẽ:
1. `test_block_choices_covers_all_domain_document_map_blocks`: `set(choices) - {"auto"} == set(domain_map)`.
2. `test_block_counts_dynamic_and_accurate`: Khớp chính xác 894 / 99 / 679 / 44 / 72.
3. `test_block_order_and_multilingual_labels_preserved`: Thứ tự và nhãn đúng định dạng trên cả 3 ngôn ngữ (vi, ja, zh-CN).
4. `test_adapter_accepts_all_blocks_in_domain_document_map`: Adapter chấp nhận từng khối trong tập 4 khối.
5. `test_adapter_unified_index_fallback_routes_all_blocks`: Fallback chỉ mục hợp nhất lọc qua trường document_id an toàn.
6. `test_adapter_rejects_unwhitelisted_blocks`: Chặn chuỗi rác / domain giả mạo.
7. `test_tong_hop_document_ids_strictly_match_map`: 72 document IDs của tong_hop khớp 100% với manifest.
8. `test_sidebar_shared_blocks_status_includes_all_four_blocks`: Sidebar hiển thị cả 4 khối tri thức.
9. `test_legacy_three_blocks_behavior_unchanged`: Hành vi của 3 khối cũ (`lsu`, `dieu_tra_loi`, `mom`) hoàn toàn không đổi.

---

## 4. Kết quả 4 Cổng Chất lượng của Repo

| Cổng | Lệnh kiểm tra | Kết quả thực tế | Trạng thái |
|---|---|---|---|
| **Cổng 1: Compileall** | `python -m compileall src tests` | 0 cú pháp lỗi | **PASS** |
| **Cổng 2: Pytest liên quan** | `pytest tests/test_block_selector_tonghop_regression.py tests/test_index_domain.py tests/test_rag_v2_adapters.py tests/test_workspace_chat_rag_v2_adapter.py tests/test_workspace_chat_app_smoke.py` | **159 / 159 tests passed** | **PASS** |
| **Cổng 3: CLI Audit** | `python -m aios_habit.cli audit` | `{"errors": [], "status": "PASS", "warnings": []}` | **PASS** |
| **Cổng 4: Import App** | `python -c "import aios_habit.workspace_chat_app"` | IMPORT APP OK | **PASS** |
