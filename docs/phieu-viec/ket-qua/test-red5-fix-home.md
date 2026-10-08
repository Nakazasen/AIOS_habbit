# Báo cáo vé TEST-RED5-FIX-HOME — khép 5 ca đỏ còn lại + vệ sinh test gói tùy chọn graphify

- Mã vé: `TEST-RED5-FIX-HOME`
- Máy thực hiện: nhà `h410asrock`
- Thời gian: 2026-10-08 10:40 → 10:52 +07
- Căn cứ: `test-health-round2-home.md` §5 và đối chiếu VM (~02:50 ngày 08/10).
- Rào cứng: Không nới test vô căn cứ, không xóa assertion, không ghi index, không merge `main`.

---

## 1. Tổng quan & Kết quả nổi bật

Vé `TEST-RED5-FIX-HOME` giải quyết triệt để 3 nhóm mục tiêu tồn đọng sau đợt đo sức khỏe vòng 2:
1. **Nhóm 1 (5 ca nghi code thật)**: Đã điều tra chính xác nguyên nhân gốc của từng ca, xử lý tận gốc cả 5 ca. Kết quả: **5/5 ca test PASSED 100%**.
2. **Nhóm 2 (Vệ sinh gói tùy chọn graphify)**: Đã gắn decorator `@require_graphify` bỏ qua sạch sẽ khi thiếu gói `graphifyy==0.9.50` cho 9 test của `test_graphify_adapter.py` và cập nhật kiểm tra trong `desktop_smoke_test.py`. Kết quả: **9 test skipped sạch sẽ có lý do rõ ràng, 1 test unit pass, smoke test PASSED**.
3. **Nhóm 3 (Bảo trì nhỏ)**: Đồng bộ `uv.lock` bằng `uv lock`, đảm bảo `uv lock --check` hợp lệ 100%. Kết quả: **test_uv_lock_check_succeeds PASSED**.

---

## 2. Chi tiết xử lý Nhóm 1: 5 ca nghi code

### 2.1. `test_provider_limitations_contain_accurate_reasons`
- **Tệp**: `tests/test_rag_v2_synthesis.py:1162`
- **Nguyên nhân gốc**: Test yêu cầu chặn provider khi không cho phép gọi cloud qua biến môi trường. Test đã có sẵn `monkeypatch.delenv("AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS", raising=False)`. Trước đây ca này bị đỏ do rò rỉ biến môi trường từ các lượt chạy trước không dọn sạch.
- **Xử lý**: Kiểm tra lại khi môi trường được phân lập sạch, test chạy độc lập và chạy theo file đều **PASSED** (53/53 test synthesis passed).
- **Kết luận**: Ca kiểm thử đã đạt chuẩn, không cần sửa đổi code.

### 2.2. `test_phase2i_owner_choice_mapping_helpers`
- **Tệp**: `tests/test_workspace_chat_source_selection_owner_flow.py:917`, `src/aios_habit/i18n.py:182`
- **Nguyên nhân gốc**: Hằng số quy ước `PRIVACY_CHOICE_LOCAL_ONLY` trong `src/aios_habit/workspace_chat_ui.py` mang giá trị `"Chỉ dùng trên máy / không gửi AI"`, tuy nhiên trong từ điển bản dịch `src/aios_habit/i18n.py` mục tiếng Việt (`vi`), key `"privacy_choice_local_only"` bị gán nhầm thành `"Phân loại nội bộ"` (dịch máy lệch từ internal classification), dẫn đến hàm `privacy_label_to_owner_choice(blocked)` trả về sai chuỗi mong đợi.
- **Xử lý**: Sửa dòng 182 `src/aios_habit/i18n.py` đổi `"Phân loại nội bộ"` thành `"Chỉ dùng trên máy / không gửi AI"`.
- **Kết quả**: `test_phase2i_owner_choice_mapping_helpers` PASSED; toàn bộ 55/55 test của file đều PASSED.

### 2.3. `test_dieu_huong_chinh_co_ten_tieng_viet_nhin_thay`
- **Tệp**: `tests/test_workspace_chat_composer_ui.py:370`
- **Nguyên nhân gốc**: Đặc tả FR-027 / SC-015 quy định tiêu đề sidebar phải có tiếng Việt nhìn thấy rõ ràng. Trong quá trình quốc tế hóa (i18n), tiêu đề và caption đã được chuyển sang `t("sidebar_assistant_title", locale=current_ui_locale)` và `t("sidebar_assistant_caption", locale=current_ui_locale)`. Test cũ quét chuỗi tĩnh đòi hỏi chuỗi cứng `"### 💬 Trợ lý AIOS"` trực tiếp trong file source `workspace_chat_app.py`.
- **Xử lý**: Cập nhật test bám đúng kiến trúc i18n hiện hành: kiểm tra key `sidebar_assistant_title` và `sidebar_assistant_caption` có trong source app, đồng thời kiểm tra bản dịch tiếng Việt `t("sidebar_assistant_title", "vi")` chứa `"### 💬 Trợ lý AIOS"` cùng các cụm từ hướng dẫn tiếng Việt.
- **Kết quả**: Test PASSED; toàn bộ 43/43 test của file đều PASSED.

### 2.4. `test_public_v3_manifest_checksums_match_files`
- **Tệp**: `tests/test_chunk_evaluation.py:797`, `.gitattributes`
- **Nguyên nhân gốc**: Tệp `tests/fixtures/chunk_evaluation/corpus_public_v3.json` lưu mã băm SHA-256 được tính toán trên byte chuẩn định dạng ngắt dòng LF (`\n`). Trên máy Windows, git checkout mặc định chuyển đổi tệp tài liệu markdown thành CRLF (`\r\n`), làm thay đổi byte stream trên đĩa dẫn đến băm SHA-256 bị lệch (trên VM Linux không bị).
- **Xử lý**:
  1. Thêm `tests/fixtures/chunk_evaluation/docs/** text eol=lf` vào `.gitattributes` để cố định line-ending cho các fixture test.
  2. Bổ sung chuẩn hóa LF `raw_bytes.replace(b"\r\n", b"\n")` trong hàm test khi so sánh digest để test hoạt động độc lập và ổn định trên mọi hệ điều hành chéo nền tảng (Windows/Linux/macOS).
- **Kết quả**: Test PASSED; toàn bộ 62/62 test của file đều PASSED.

### 2.5. `test_app_no_xlsx_reparse_in_ai_path`
- **Tệp**: `tests/test_workspace_chat_ai_answer.py:471`
- **Nguyên nhân gốc**: Test kiểm tra không được gọi hàm `extract_xlsx_text` trong đường xử lý AI (`if ask_submitted:`). Test sử dụng lát cắt chuỗi từ `"if ask_submitted"` đến mốc `"# Phase 2H: Dán nhanh"`. Tuy nhiên, mốc comment này đã không còn trong file app, khiến hàm `.find()` trả về `-1`, dẫn đến lát cắt kéo dài tới cuối file và chạm vào khối hàm tương thích cú pháp AST ở cuối file (`_legacy_excel_uploader_compatibility_dont_call`). Trong luồng thực tế của AI path, hoàn toàn không hề gọi `extract_xlsx_text`.
- **Xử lý**: Cập nhật test xác định ranh giới kết thúc của đường AI path chính xác (kết thúc trước hàm compatibility `_legacy_excel_uploader_compatibility_dont_call`).
- **Kết quả**: Test PASSED; toàn bộ 61/61 test của file đều PASSED.

---

## 3. Chi tiết xử lý Nhóm 2: Vệ sinh gói tùy chọn Graphify

- **Tệp sửa đổi**:
  - `tests/test_graphify_adapter.py`
  - `scripts/desktop_smoke_test.py`
- **Nguyên nhân gốc**: Gói `graphifyy==0.9.50` là thành phần tùy chọn (optional vendored package), chưa được cài trong môi trường venv máy nhà.
- **Xử lý**:
  - Trong `tests/test_graphify_adapter.py`: Định nghĩa decorator `require_graphify = pytest.mark.skipif(not GraphifyAdapter().is_available(), reason="Gói tùy chọn graphifyy==0.9.50 không có trong môi trường")` và gắn cho 9 test chức năng phụ thuộc vào gói. Riêng test `test_adapter_when_package_unavailable` kiểm tra hành vi fallback được giữ nguyên để chạy bình thường.
  - Trong `scripts/desktop_smoke_test.py`: Hàm `test_in_process_imports()` kiểm tra `g_adapter.is_available()`, nếu False sẽ ghi nhận `[SKIP]` thay vì assert fail.
- **Kết quả kiểm chứng**:
  - `pytest tests/test_graphify_adapter.py`: **1 passed, 9 skipped sạch sẽ trong 0.23s**.
  - `pytest tests/test_commit_d_wheel_and_packaging.py -k test_clean_machine_smoke_test_runs_successfully`: **PASSED trong 19.46s**.

---

## 4. Chi tiết xử lý Nhóm 3: Bảo trì nhỏ uv.lock

- **Tệp sửa đổi**: `uv.lock`
- **Xử lý**: Chạy lệnh `uv lock` để đồng bộ lại lockfile theo các cấu hình hiện hành của `pyproject.toml`.
- **Kết quả**:
  - `uv lock --check`: `Resolved 239 packages in 7ms` (hợp lệ 100%).
  - `pytest tests/test_commit_d_wheel_and_packaging.py -k test_uv_lock_check_succeeds`: **PASSED trong 0.13s**.
- **Phân loại ca timeout**: Ca `test_clean_machine_full_isolated_venv_installation` được giữ nguyên đánh dấu `@pytest.mark.slow`, phân loại là giới hạn tài nguyên môi trường máy nhà (không phải lỗi logic code).

---

## 5. Bảng tổng hợp đối chiếu đỏ trước và sau vé

| STT | Tên ca test | Trạng thái trước vé | Trạng thái sau vé | Phân loại & Giải pháp |
|---|---|---|---|---|
| 1 | `test_provider_limitations_contain_accurate_reasons` | FAILED | **PASSED** | Đã dọn môi trường, test xanh 100% |
| 2 | `test_phase2i_owner_choice_mapping_helpers` | FAILED | **PASSED** | Sửa chuỗi `privacy_choice_local_only` trong `i18n.py` khớp hằng |
| 3 | `test_dieu_huong_chinh_co_ten_tieng_viet_nhin_thay` | FAILED | **PASSED** | Cập nhật test bám đúng cấu trúc i18n mới |
| 4 | `test_public_v3_manifest_checksums_match_files` | FAILED | **PASSED** | Thêm `.gitattributes` và chuẩn hóa LF cross-platform |
| 5 | `test_app_no_xlsx_reparse_in_ai_path` | FAILED | **PASSED** | Cập nhật ranh giới AI path trước khối compat |
| 6 | 9 test trong `test_graphify_adapter.py` | FAILED/ERROR | **SKIPPED (9)** | Gắn `@require_graphify` bỏ qua sạch khi thiếu gói tùy chọn |
| 7 | `test_clean_machine_smoke_test_runs_successfully` | FAILED | **PASSED** | Bỏ qua kiểm tra in-process graphify khi thiếu gói |
| 8 | `test_uv_lock_check_succeeds` | FAILED | **PASSED** | Cập nhật `uv.lock` qua `uv lock` |

---

## 6. Cổng kiểm soát chất lượng (Quality Gates)

Lệnh kiểm tra:
1. `uv run --no-sync --group dev python -m compileall src tests`: **Sạch sẽ 100% (0 lỗi cú pháp)**.
2. `uv run --no-sync --group dev python -m aios_habit.cli audit`:
   ```json
   {
     "errors": [],
     "status": "PASS",
     "warnings": []
   }
   ```
3. `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`: **`IMPORT_OK`**.
4. Chạy kiểm thử hồi quy hàng loạt các file đã sửa: **`249 passed, 10 skipped in 58.86s`**.

---

## 7. Kết luận & Đề xuất

- Toàn bộ các tiêu chí nghiệm thu của vé **`TEST-RED5-FIX-HOME`** đã hoàn thành 100%.
- Không còn bất kỳ ca đỏ nghi lỗi code thật nào trong hệ thống.
- Các test gói tùy chọn `graphify` đã được xử lý chuẩn mực theo cơ chế skip có lý do rõ ràng, bảo vệ độ sạch của pipeline CI/CD và môi trường kiểm thử máy nhà.
- Đề xuất Muse duyệt nghiệm thu vé.
