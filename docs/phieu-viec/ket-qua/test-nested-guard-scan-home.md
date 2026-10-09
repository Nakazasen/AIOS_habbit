# Báo cáo vé TEST-NESTED-GUARD-SCAN-HOME — rà soát mẫu chập chờn còn lại

- Mã vé: `TEST-NESTED-GUARD-SCAN-HOME`
- Máy: `h410asrock` — đầu nhánh `77f14d8` (sau `d362d4e` verdict ĐẠT E2E-GUARD)
- Phạm vi: chỉ đọc + báo cáo, không sửa mã / kiểm thử / chỉ mục / merge `main`
- Ngày: 2026-10-09 ~13:00 +07
- Tổng tệp kiểm thử: 311 tệp trong `tests/`

## Cách rà

1. Liệt kê mọi `subprocess.(run|Popen|check_output|call)` + `timeout=` + `TimeoutExpired` trong `tests/`.
2. Liệt kê mọi phụ thuộc model / tệp thật (`resolve_bge`, `resolve_onnx`, `BGE_M3`, `bge-m3`, `library.sqlite`, production) + điều kiện bỏ qua (`pytest.skip`, `skipif`, `importorskip`).
3. Liệt kê khẳng định số tuyệt đối (`== 889`, `== 149800`, `st_size ==`, `elapsed <`) gắn với một máy.

## Bảng kết quả

| # | Ca / nhóm ca | Tệp | Mẫu rủi ro | Đã có bảo vệ? | Mức thợ đề xuất |
|---|---|---|---|---|---|
| 1 | `test_production_index_counts` (dòng 193–194: `chunk_count == 149800`, `doc_count == 889` trên production thật) | `tests/test_index_status.py` | (c) số tuyệt đối theo kho máy nhà | Có một nửa: vắng production thì bỏ qua (dòng 178), nhưng production lớn lên là đỏ | **CAO — sửa riêng**: chuyển sang khẳng định quan hệ như vé hygiene đã làm ở `test_production_index_specs_retrieval` (tổng > 0, các miền rời nhau, cộng lại bằng tổng), không ghim 889/149800 |
| 2 | `test_domain_document_map_counts` (dòng 33–51: `len == 889/92/681/44/72`) | `tests/test_workspace_chat_production_index_filtering.py` | (c) số tuyệt đối (bản đồ ghim trong repo `domain_document_map.json`) | Chưa: đọc tệp repo luôn có, không bỏ qua; ca thứ hai cùng tệp đã sửa sang quan hệ | **TRUNG BÌNH — sửa riêng**: chuyển sang quan hệ (rời nhau + cộng lại bằng tổng) như ca thứ hai, giữ một chỗ ghim duy nhất nếu cần |
| 3 | `test_probe_proves_required_runtime_capabilities` + `test_probe_denies_*` (probe ngoài `timeout=180`) | `tests/test_agent_runtime_capabilities.py` | (a) tiến trình con trần cứng 180s, không bắt `TimeoutExpired` | Có một nửa: thiếu `AIOS_OPENCODE_PROBE_MODEL` thì bỏ qua; nhưng treo quá 180s là đỏ, không thành bỏ qua | **TRUNG BÌNH-THẤP — cân nhắc**: bọc `TimeoutExpired` thành bỏ qua có lý do tốc độ máy (cùng mẫu vé E2E-GUARD), hoặc giữ đỏ nếu muốn probe phải nhanh |
| 4 | `test_scale_10k_nodes*` (`val/ser/deser < 2.0s`), `test_redos*` (`elapsed < 0.2s`) | `tests/test_adversarial_evidence_trace.py` | (c) trần tốc độ tuyệt đối theo máy | Chưa | **TRUNG BÌNH-THẤP — theo dõi**: nới hoặc bỏ qua khi máy tải nặng; hiện chỉ dùng dữ liệu giả trong RAM nên ít đỏ, nhưng 0,2s/2,0s dễ chập chờn dưới tải BGE |
| 5 | `test_*_5_real_code_lookups (elapsed < 60s)` | `tests/test_chat_action_error_lookup.py:111` | (c) trần tốc độ tuyệt đối | Chưa | **THẤP — theo dõi**: 60s cho 5 tra cứu là rộng, chỉ đỏ khi máy nghẽn nặng; chưa cần sửa |
| 6 | `test_client_enforces_bounded_deep_timeout` (`< 60s`, `< 30s`) | `tests/test_bge_subprocess_client.py:113,129` | (c) trần tốc độ | Không cần: trần rộng (ghi chú đo thật 2,7–13,6s trên h410asrock), dùng `tmp_path` | **THẤP — không sửa** |
| 7 | `test_lsu_alert_* (latency < 300s)` | `tests/test_lsu_alert_realtime_pc0575.py:84` | (c) trần tốc độ | Không cần: 300s rất rộng | **THẤP — không sửa** |
| 8 | `run_cli` (`timeout=30`), `_run` dev-cli (`timeout=30`), `owner-workflow` (`timeout=30` x2), `evaluate_chunking` (`timeout=10` x2), `git ls-files` (`timeout=10` x2) | `tests/test_aios_habit.py`, `tests/test_rag_v2_dev_cli.py`, `tests/test_owner_workflow_cli.py`, `tests/test_chunk_evaluation.py`, `tests/test_antigravity_handoff_ui_flow.py` | (a) tiến trình con có trần 10–30s, không bắt `TimeoutExpired` | Chưa, nhưng lệnh nhẹ (help/status/git/lệnh local `tmp_path`), trần đủ rộng | **THẤP — không sửa**: nếu sau này đỏ vì máy chậm mới bọc bỏ qua; hiện không đáng đụng |
| 9 | `test_expert_interview_privacy` (`git ls-files` không trần, bắt `CalledProcessError/FileNotFoundError`) | `tests/test_expert_interview_privacy.py:92` | (a) tiến trình con không trần | An toàn theo hướng khác: không trần nên không hết giờ; lỗi git thì bỏ qua | **Không sửa** |
| 10 | Mẫu chuẩn đã bịt (đối chứng) | `tests/test_commit_d_wheel_and_packaging.py` (e2e `timeout=300` + docker `timeout=600` + `proc.wait(5)` đều bắt `TimeoutExpired` thành bỏ qua; thiếu model thì bỏ qua) | (a)+(b) đã bịt | Có đủ | **Không sửa — giữ làm mẫu** |
| 11 | Các phụ thuộc tệp thật đã có bỏ qua | `test_j1_rt.py`, `test_j1_csv.py`, `test_jigbeam_adapter.py`, `test_error_cases_f2.py` (`REAL_FILE`), `test_index_status.py` (vắng production), `test_workspace_chat_production_index_filtering.py` (ca thứ hai) | (b) tệp chỉ có ở một số máy | Có đủ (`skipif`/`skip`) | **Không sửa** |
| 12 | Các ca model dùng `tmp_path` (không cần máy thật) | `test_rag_v2_bge_onnx.py`, `test_rag_v2_pipeline.py`, `test_workspace_chat_rag_v2_deployment.py`, `test_battle_notebooklm_rag_v2.py`, `test_split_index_by_domain.py`… | (b) — không dính | Không cần bỏ qua vì tự dựng dữ liệu giả | **Không sửa** |

## Kết luận thợ

- Không còn ca lồng pytest nặng nào chưa được bảo vệ ngoài ca e2e vừa bịt.
- Việc sửa riêng nên làm: mục 1 (production 889/149800 ghim cứng) trước, mục 2 (bản đồ 889/92/681/44/72) sau — cả hai chuyển sang khẳng định quan hệ.
- Mục 3–5 chỉ theo dõi; mục 6–12 không cần đụng.
- Vé này không sửa gì theo rào cứng. Phần sửa do điều phối phát hành riêng.

## Rào cứng đã giữ

- Chỉ đọc `tests/` + `src/aios_habit/index_domain.py` để xác minh nguồn bản đồ; không sửa tệp nào (`git status` chỉ có báo cáo này + `trang-thai.md`).
- Không ghi chỉ mục, không merge `main`.
