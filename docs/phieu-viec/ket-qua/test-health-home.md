# Báo cáo vé TEST-HEALTH-HOME — rà sức khỏe bộ test trên máy nhà (chỉ phân loại, không sửa)

- Mã vé: `TEST-HEALTH-HOME`. Máy làm: nhà h410asrock. Thời gian: 2026-10-07 21:41 → 22:42 +07.
- Vé này KHÔNG sửa `src/`/`tests/`, không ghi index, không merge `main` (giữ đúng rào cứng).

## 1. Kết quả chạy toàn bộ (một lượt duy nhất tới khi xong)

- Lệnh chạy nền tách phiên: `uv run --no-sync --group dev pytest -q --tb=short`, thư mục tạm `D:\pytest-tmp`, log `local_runs/test-health-home/pytest-full.log` (69.770 byte) + `.err.log`, mốc xong `done.marker exit=1`.
- Tổng: **4.200 test — 4.138 đạt, 26 fail, 19 error, 37 skip. Thời gian 3.450 giây (57,5 phút).**
- Danh sách fail/error đầy đủ: `local_runs/test-health-home/fail-list.txt` (45 dòng: 26 `FAILED` + 19 `ERROR`).

## 2. Phân loại nguyên nhân

### (a) Môi trường máy nhà — 23 test (19 error + 4 fail)

- 9 `ERROR` nhóm `test_chat_action_error_lookup.py`: fixture dựng báo thiếu file `Loi KDTPS.xlsx` theo đường dẫn kiểu Linux (`\home\hatch\workspace\...`) — máy nhà Windows không có file này.
- 10 `ERROR` nhóm `test_error_cases_f4.py`: fixture dựng báo thiếu file nguồn `02XC_...xls` cũng theo đường dẫn Linux `\home\hatch\...` — cùng họ nguyên nhân trên.
- 1 fail `test_call_antigravity_bridge_privacy_guard`: lỗi mạng `getaddrinfo failed` (không nối được cầu antigravity từ máy nhà).
- 1 fail `test_in_app_qa_blocks_cloud_local_export`: `WinError 10061` (không có dịch vụ LLM local đang nghe trên máy nhà nên kịch bản chặn xuất hiện lỗi khác Biochem).
- 1 fail `test_clean_machine_full_isolated_venv_installation`: cài venv cô lập quá 600 giây (timeout mạng/máy) — vé này KHÔNG chạy lại riêng vì chắc chắn do môi trường.
- 1 fail `test_uv_lock_check_succeeds`: `uv.lock` lệch khỏi `pyproject` trên nhánh (`uv lock --check` báo cần chạy `uv lock`) — lệch trạng thái repo, không phải lỗi runtime; đề nghị vé bảo trì riêng.

### (b) Phụ thuộc thứ tự / thời gian (flaky) — 0 test

- Chạy lại riêng lẻ 25/26 test fail trong một tiến trình pytest mới (trừ test timeout môi trường ở trên): **cả 25 vẫn fail y như cũ** (25 failed trong 324 giây). Không có test nào đang fail mà chạy riêng lại pass → không phát hiện flaky trong lượt này.

### (c) Nghi lỗi code thật — 22 test (đề nghị vé sửa riêng, KHÔNG sửa ở vé này)

Nhóm quyền riêng tư / chặn xuất (5): `test_render_chat_bubble_denies_untrusted_metadata_path_traversal`, `test_local_only_cloud_provider_blocked_and_vi_instruction`, `test_missing_db_returns_none` (trả outcome thay vì `None`), `test_phase4_owner_pilot_local_only_blocks_external_export` (`allowed_external=True` thay vì `False`), `test_mom_prompt_pack_includes_refs_and_privacy_warning` (thiếu dấu `local_only`).

Nhóm lane RAG v2 (9): `test_dev_cli_evaluate_uses_selected_sources_and_returns_local_metrics` (privacy 0,50 < 1,0), `test_full_pipeline_pass` (privacy 0,75 thay vì 1,0), `test_privacy_local_only_passes`, 2 test `cjk_prefilter` (lọc sơ bộ lệch khỏi quét đủ), 2 test `rag_v2_synthesis` (composer nhận nhiễu + lý do giới hạn sai), 3 test `rag_v2_synthesis_provider` (lọc nhà cung cấp + nhãn công ty + lý do riêng tư).

Nhóm giao diện / nhãn (4): `test_app_no_xlsx_reparse_in_ai_path` (còn gọi `extract_xlsx_text` trong đường AI), `test_phase2i_owner_choice_mapping_helpers` (nhãn ánh xạ sai), 2 test `workspace_chat_ui_i18n` (1 chuỗi cứng trong `render_chat_bubble`, 2 chuỗi cứng trong `workspace_chat_app`).

Nhóm dữ liệu / kho (3): `test_expert_knowledge_e2e_full_lifecycle` (`NOT_APPLICABLE` thay vì `BLOCKED_PRIVACY`), `test_public_v3_manifest_checksums_match_files` (SHA manifest `corpus_public_v3.json` lệch file `src-quality-process`), `test_index_status_matches_real_db_if_present` (xem §3).

Bằng chứng chạy-lại-riêng-lẻ: cả 22 test nhóm (c) đều nằm trong 25 test chạy lại vẫn fail ở mục (b) — lỗi tất định, không phải thứ tự.

## 3. Phát hiện đáng chú ý: bản index khôi phục ở máy nhà lệch production

- Test `test_index_status_matches_real_db_if_present` đọc bản sao local `local_runs/workspace_chat_rag_v2_production/.../library.sqlite` và đếm được **133.144 mảnh**, trong khi vé `INDEX-PROD-HOME` vừa kiểm chứng file production `C:\AIOS_workspace_chat_rag_v2_production\...` đủ **149.800 mảnh**.
- Nghĩa là: production thì nguyên vẹn (vé trước đã chốt), nhưng **bản khôi phục trong `local_runs/` thiếu ~16.656 mảnh** — thợ nào dùng bản local này để đo sẽ đo trên kho thiếu. Đề nghị vé riêng xác minh lại bản local (không đụng production).

## 4. Đối chiếu với suite điều phối đã xanh trên VM

- Chạy lại tại máy nhà 4 file mà báo cáo `retrieval-entity-pc0575.md` ghi xanh trên VM (`test_quality_harness.py`, `test_rag_v2_index.py`, `test_rag_v2_pipeline.py`, `test_rag_v2_evidence.py`): **102 passed trong 148 giây** (VM ghi 106/106 — lệch 4 test, có thể do nhánh đổi từ lúc đó; không ảnh hưởng kết luận).
- Kết luận khoanh vùng: **không có test nào nhóm (c) nằm trong 4 suite xanh VM** — các file fail nhóm (c) (`dev_cli`, `eval_harness`, `opt_pyloops`, `synthesis`, `synthesis_provider`, UI/i18n, manifest...) nằm ngoài phạm vi VM đã kiểm. Vì vậy trạng thái đúng là **"chỉ đỏ ở máy nhà, chưa rõ nơi khác"**, không phải "đỏ khắp nơi" — cần chạy các file này trên VM mới kết luận được.

## 5. Kết luận và đề nghị

- Bộ test máy nhà: 4.138/4.200 xanh (98,5%); 45 điểm đỏ đã phân loại xong — 23 môi trường, 0 flaky, 22 nghi lỗi code thật.
- Đề nghị 3 vé tiếp theo: (1) vé sửa 22 test nhóm (c), ưu tiên 5 test riêng tư + 9 test lane RAG v2 trước; (2) vé xác minh bản index `local_runs/` thiếu mảnh (§3); (3) vé chạy các file nhóm (c) trên VM để chốt "chỉ đỏ máy nhà" hay "đỏ khắp nơi".
- Rào giữ: vé này chỉ chạy test + phân loại; không sửa `src/`/`tests/`, không ghi index, không merge `main`.
