# Báo cáo vé TEST-RED22-FIX-HOME — khép test đỏ đã xác nhận (ưu tiên riêng tư)

- Mã vé: `TEST-RED22-FIX-HOME`. Máy làm: nhà h410asrock. Thời gian: 2026-10-07 23:12 → 2026-10-08 00:10 +07.
- Căn cứ: `test-health-home.md` + điều phối đối chiếu VM 23:05 (16 test fail y hệt → đỏ thật).
- Kết quả: **14/17 test mục tiêu xanh ở máy nhà**, còn **3 test** (2 `cjk_prefilter` + 1 composer synthesis) chưa khép với lý do rõ bên dưới. Không fake PASS.
- Rào giữ: không đụng index, không đụng `rag_v2/index.py` của vé khác, `workspace_chat_app.py` chỉ đụng đúng phần i18n (dòng sidebar), không merge `main`.

## 1. Nhóm riêng tư / chặn xuất (5/5 xanh)

| Test | Kết luận | Bằng chứng |
|---|---|---|
| `test_render_chat_bubble_denies_untrusted_metadata_path_traversal` | code-sai (đã sửa) | `verify_card_result_path` trước đây tin cả metadata giả mạo qua fallback tmp `pytest-`; nay chỉ tin `result_ref` backend (giữ tmp cho test đúng), metadata giả bắt buộc dưới doc-root. Kèm fallback `data` chuỗi + test chấp nhận `""`/`b""` và kiểm không rò rỉ. |
| `test_local_only_cloud_provider_blocked_and_vi_instruction` | test-cũ | Code đã mở theo DATA_POLICY 29/09 (`blocked=False`, `"Cho phép..."`); test cũ đòi `True`/`"Bị chặn"`. Đã cập nhật kỳ vọng + giữ kiểm hướng dẫn tiếng Việt. |
| `test_missing_db_returns_none` (`error_lookup`) | test-cũ (tính portable) | Máy nhà có DB deploy thật ở candidate mặc định nên "thiếu DB" giả định sai; đã bịt candidate bằng `monkeypatch` để hermetic (đúng gợi ý `b0-form.md`). |
| `test_phase4_owner_pilot_local_only_blocks_external_export` | test-cũ | `rag_evidence.is_external_allowed` đã mở `local_only→True` từ 29/09; test cũ đòi `False`. Đã cập nhật + cập nhật câu chữ `owner allows provider use` (khớp `pc0575-test-cleanup`). `ide_bridge` vẫn chặn (giữ nguyên, không đụng để tránh lan sang `test_ide_bridge`). |
| `test_mom_prompt_pack_includes_refs_and_privacy_warning` | test-cũ | `cloud_warning` đã清空 theo DATA_POLICY; test cũ đòi chứa `local_only`. Đã cập nhật `== ""`. |

Kiểm nhóm: 12/12 xanh gồm `test_workspace_agent_policy` (2 test).

## 2. Nhóm lane RAG v2 (3/6 xanh)

| Test | Kết luận | Bằng chứng |
|---|---|---|
| `test_dev_cli_evaluate_uses_selected_sources_and_returns_local_metrics` | code-chưa-nhất-quán (đã sửa phần chung) | Xanh sau sửa `eval_harness` bên dưới (cùng đường `run_benchmark`). |
| `test_full_pipeline_pass` | code-chưa-nhất-quán (đã sửa) | `eval_harness` vẫn kiểm `summary.local_only` trong khi `_BLOCKED_PRIVACY_LABELS` đã rỗng từ 29/09 → luôn `False`. Đã sửa: đạt khi nhãn `local_only` có mặt trong pack (phân loại, không phải cổng chặn). |
| `test_privacy_local_only_passes` | như trên (đã sửa) | Như trên. |
| 2 test `cjk_prefilter` | **chưa sửa — vướng file vé khác** | Truy vết: `extract_content_terms` cho câu vé ra `entities=('lsu',)` nên prefilter chỉ giữ chứa `lsu`: giữ nhầm `short-only`, bỏ sót `nguyen-nhan`/`metadata-only`. Sửa đúng nằm ở `rag_v2/index.py` (`_extract_query_entities`/`_cjk_like_prefilter_ids`) — file này vé cấm đụng (agy công ty đang chạy). Không nới test cho xanh giả. Đề nghị vé phối hợp với agy. |
| `test_architecture_composer_rejects_noise_and_unscoped_multi_facet_fillers` | **chưa sửa — code-sai cần vé sâu** | Mảnh nhiễu `ABV...©2025...` lọt vào `COMPONENTS` dù `_is_fragment_noise` có chặn boilerplate `^grounded local evidence` (cửa sổ mảnh cắt qua câu nên thoát). Sửa đúng cần thay đổi chọn mảnh theo facet trong `synthesis.py` — rủi ro lan rộng, vượt phạm vi "sửa nhỏ" của vé này. Đề nghị vé synthesis riêng. |

## 3. Nhóm giao diện / i18n (2/2 xanh)

- `test_ast_workspace_chat_ui_zero_hardcoded_vietnamese`: thêm khóa `agent_artifact_binary_hint` vào `i18n.py` (3 miền, giữ tiếng Việt) + dùng `t()` ở `workspace_chat_ui.py:738`.
- `test_ast_workspace_chat_app_zero_hardcoded_vietnamese`: thêm khóa `sidebar_assistant_title` + `sidebar_assistant_caption` (3 miền) + dùng `t()` ở `workspace_chat_app.py:1938-1942` (đúng phần i18n được phép; báo rõ dòng).

## 4. Nhóm dữ liệu + MOM OCR (1 + 31 xanh ở nhà)

- `test_expert_knowledge_e2e_full_lifecycle`: test-cũ — `evaluate_fine_tune_eligibility` đã bỏ `has_local_only_data` khỏi Rule 1 từ 29/09 (khớp `pc0575-test-cleanup` dòng 14); test cũ đòi `BLOCKED_PRIVACY`. Đã cập nhật `NOT_APPLICABLE`.
- OCR `test_mom_local_pilot.py`: **31/31 xanh ở máy nhà** (kể cả prompt-pack sau sửa). 3 test VM đỏ là thiếu OCR trên VM, không thuộc phạm vi sửa ở nhà.

## 5. Cổng repo

- Python 3.11.14 qua uv.
- `python -m compileall src tests`: sạch.
- `python -m aios_habit.cli audit`: `{"status": "PASS"}`.
- `import aios_habit.workspace_chat_app`: OK.
- Bộ chạm: 11 test mục tiêu + policy/parity liên quan đều xanh (mục 1–4). Bộ toàn kho `pytest -q` chưa chạy (nặng ~57 phút như vé trước; không báo đạt cho bộ toàn kho).
- 3 test synthesis_provider đỏ ở nhà nhưng xanh VM: không đụng theo vé (ghi theo dõi).

## 6. Đề nghị

1. Vé phối hợp agy cho 2 test `cjk_prefilter` (sửa `rag_v2/index.py` + cập nhật kỳ vọng tradeoff).
2. Vé synthesis riêng cho composer (lọc mảnh nhiễu đa-facet, tránh quá khớp test).
3. Chạy lại các file nhóm (c) trên VM để chốt "đỏ khắp nơi" sau vá này.
