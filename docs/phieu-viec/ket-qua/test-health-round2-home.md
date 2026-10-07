# Báo cáo vé TEST-HEALTH-ROUND2-HOME — chạy lại toàn bộ test ở máy nhà, đối chiếu vòng 1

- Mã vé: `TEST-HEALTH-ROUND2-HOME`. Máy làm: nhà h410asrock. Thời gian: 2026-10-08 02:03 → 02:34 +07.
- Vé này KHÔNG sửa `src/`/`tests/`, không ghi index, không merge `main` (giữ đúng rào cứng).

## 1. Kết quả chạy toàn bộ (một lượt duy nhất tới khi xong)

- Lệnh chạy nền tách phiên: `uv run --no-sync --group dev pytest -q --tb=short`, thư mục tạm `D:\pytest-tmp`, log `local_runs/test-health-round2-home/pytest-full.log` (65.292 byte) + `.err.log`, mốc xong `done.marker exit=1`.
- Tổng: **4.228 lượt thu thập — 4.153 đạt, 19 fail, 19 error, 37 skip. Thời gian 1.852,75 giây (30,9 phút).**
- Vòng 1 (để so): 4.220 lượt — 4.138 đạt, 26 fail, 19 error, 37 skip, 3.450 giây (57,5 phút).
- Chênh thu thập +8 lượt (có 11 ca mới xuất hiện lần đầu: 9 `graphify_adapter` + 1 smoke + 1 `dieu_huong`; bù lại 3 lượt cũ không còn thu thập sau các commit sửa giữa hai vòng).
- Danh sách fail/error đầy đủ: `local_runs/test-health-round2-home/fail-list.txt` (38 dòng: 19 `FAILED` + 19 `ERROR`).
- Điều kiện chạy: máy sạch, không có vé khác tranh tài nguyên (chỉ có BGE worker con của chính pytest + MCP harness nhẹ); Python 3.11.14 qua uv; đĩa C ~11GB / D ~42GB.

## 2. Đối chiếu từng điểm đỏ với bảng phân loại vòng 1

### (a) Đỏ cũ nhóm môi trường — còn nguyên 23/23

- 19 `ERROR` y hệt vòng 1: 9 `test_chat_action_error_lookup` (thiếu file `Loi KDTPS.xlsx` đường dẫn Linux) + 10 `test_error_cases_f4` (thiếu file nguồn đường dẫn Linux).
- 4 `FAILED` y hệt vòng 1: `test_call_antigravity_bridge_privacy_guard` (mạng), `test_in_app_qa_blocks_cloud_local_export` (WinError 10061, không có LLM local), `test_clean_machine_full_isolated_venv_installation` (timeout), `test_uv_lock_check_succeeds` (lock lệch).
- Riêng `test_index_status_matches_real_db_if_present`: đã XANH (không còn trong danh sách đỏ) — xác nhận vé sửa đường đọc production đã khép, đúng như vé ghi.

### (b) Đỏ cũ nhóm code — đã khép 18/22

Đã xanh trở lại (không còn trong danh sách đỏ): 5 riêng tư (`omnibar`, `handoff`, `missing_db`, `mom_prompt`, `phase4`), `expert_e2e`, `dev_cli`, 2 `eval_harness`, 2 `cjk_prefilter`, `composer_rejects_noise`, 3 `synthesis_provider`, 2 `ui_i18n`. Chi tiết từng ca ở §4.

Còn đỏ 4 ca (vẫn fail y như vòng 1): `manifest_checksums`, `provider_limitations`, `app_no_xlsx_reparse`, `phase2i_mapping` — phân loại cuối ở §5.

### (c) Đỏ MỚI chưa từng xuất hiện ở vòng 1 — 11 ca, truy vết tới gốc

Chạy lại riêng lẻ 3 ca đại diện trong một tiến trình pytest mới: **cả 3 vẫn fail y hệt (3 failed trong 26,83 giây)** — lỗi tất định, không phải flaky.

1. 9 test `test_graphify_adapter.py` — GỐC: gói tùy chọn `graphifyy==0.9.50` không có trong venv máy nhà (kiểm chứng: `find_spec('graphifyy')` ra `None`; log báo `Graphify package ('graphifyy==0.9.50') is not available`). Kết luận: **môi trường** (thiếu gói tùy chọn), không phải lỗi logic. Vé nối tiếp: hoặc cài gói, hoặc gắn cờ bỏ qua khi thiếu gói.
2. 1 test `test_clean_machine_smoke_test_runs_successfully` — GỐC: cùng gốc trên (smoke test gọi `g_adapter.is_available()`, nhận `False`). Kết luận: **môi trường** (hệ quả của ca 1).
3. 1 test `test_dieu_huong_chinh_co_ten_tieng_viet_nhin_thay` — GỐC: test đọc `src/aios_habit/workspace_chat_app.py` và đòi chuỗi `### 💬 Trợ lý AIOS`, nhưng grep toàn file không còn chuỗi này (tiêu đề đã đổi sau các đợt sửa UX). Chạy riêng vẫn fail. Kết luận: **nghi code/UI thật** (test bám nhãn FR-027/SC-015 mà code chưa có) — cần vé sửa riêng, không đoán là test cũ hay code lùi.

## 3. Riêng 3 test synthesis_provider (vòng 1 đỏ ở nhà, xanh trên VM)

- Cả 3 (`test_privacy_filters_cloud_providers`, `test_no_providers_raises_with_privacy_reason`, `test_safety_mode_label_company_when_local_only`) đều **XANH** ở vòng 2 (không còn dòng FAILED nào chứa `synthesis_provider` trong log đầy đủ).
- Kết luận: **lệch máy đã hết** — đúng như kỳ vọng sau chùm sửa (riêng tư + eval + prefilter + composer). Không cần truy vết môi trường thêm.

## 4. Bảng đối chiếu vòng 1 → vòng 2 (tóm tắt)

| Nhóm | Vòng 1 | Vòng 2 | Thay đổi |
|---|---|---|---|
| Đạt | 4.138 | 4.153 | +15 |
| Fail | 26 | 19 | −7 |
| Error | 19 | 19 | 0 (y hệt) |
| Skip | 37 | 37 | 0 |
| Môi trường (fail+error) | 23 | 33 | +10 (mới: 9 graphify + 1 smoke) |
| Nghi code thật | 22 | 5 | −17 (khép 18, mới 1 `dieu_huong`) |
| Flaky | 0 | 0 | 0 (ca mới chạy riêng đều fail) |
| Thời gian chạy | 57,5 phút | 30,9 phút | nhanh gần gấp đôi |

18 ca khép: 5 riêng tư + `expert_e2e` + `dev_cli` + 2 `eval_harness` + 2 `cjk_prefilter` + `composer_noise` + 3 `synthesis_provider` + `index_status` + 2 `ui_i18n`.

## 5. Danh sách đỏ còn lại kèm phân loại cuối cùng (38 ca)

Môi trường (33): 19 error §2(a) + 4 fail §2(a) + 10 fail mới §2(c) mục 1–2.
Nghi code thật (5):
- `test_public_v3_manifest_checksums_match_files` — băm manifest lệch file `src-quality-process` (chạy riêng vẫn fail; cần vé tạo lại manifest).
- `test_provider_limitations_contain_accurate_reasons` — thiếu `cloud_privacy_blocked` trong lý do giới hạn (đỏ cũ từ trước vé composer, đã đối chiếu `stash` đỏ y hệt — cần vé sửa sâu tầng synthesis).
- `test_app_no_xlsx_reparse_in_ai_path` — còn gọi `extract_xlsx_text` trong đường AI (y vòng 1).
- `test_phase2i_owner_choice_mapping_helpers` — ánh xạ nhãn sai (y vòng 1).
- `test_dieu_huong_chinh_co_ten_tieng_viet_nhin_thay` — thiếu tiêu đề `### 💬 Trợ lý AIOS` trong app (mới, §2(c) mục 3).
Flaky: 0.

## 6. Cổng repo và ghi chú nghiệm thu

- `compileall src tests`: sạch. `cli audit`: `PASS`. `import workspace_chat_app`: OK.
- Vé này là vé đo (chỉ chạy + phân loại, rào cấm sửa): bằng chứng là log chạy thật toàn bộ (65.292 byte) + `fail-list.txt` 38 dòng + số đo thời gian thật 30,9 phút. Không có giao diện mới nên không có ảnh chụp màn hình; không sửa code nên không có hồi quy code.
- Đề nghị vé tiếp theo: (1) vé môi trường graphify (cài gói `graphifyy==0.9.50` hoặc gắn cờ bỏ qua + smoke xanh theo); (2) vé sửa 5 ca nghi code thật (ưu tiên `provider_limitations` + `dieu_huong` + manifest); (3) vé bảo trì `uv.lock` + timeout venv cô lập.
- Rào giữ: vé này chỉ chạy test + phân loại; không sửa `src/`/`tests/`, không ghi index, không merge `main`.
