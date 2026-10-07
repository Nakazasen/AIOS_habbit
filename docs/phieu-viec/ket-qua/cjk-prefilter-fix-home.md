# Báo cáo vé CJK-PREFILTER-FIX-HOME — sửa tầng lọc sơ bộ giữ sai mảnh

- Mã vé: `CJK-PREFILTER-FIX-HOME`. Máy làm: nhà h410asrock. Thời gian: 2026-10-08 01:50 → 02:15 +07.
- Căn cứ: `prompt.md` vé này + báo cáo `test-red22-fix-home.md` mục 2 (truy vết: thực thể trích được quá hẹp).
- Kết quả: **2/2 test đích xanh**, hồi quy liên quan **79/79 xanh**, cổng repo đủ (Python 3.11, `compileall` sạch, `cli audit` PASS, `import workspace_chat_app` thành công). Không ghi chỉ mục thật, chỉ dùng chỉ mục tạm của kiểm thử.

## 1. Lỗi gặp

- Với câu hỏi của vé, `extract_content_terms` cho ra nhiều thuật ngữ (trong đó có `beam径`, `nguyên`), nhưng `_cjk_like_prefilter_ids` lại rẽ nhánh riêng: khi có thực thể thì **chỉ dùng thực thể** (`entities=('lsu',)`).
- Hậu quả: tầng lọc sơ bộ chỉ giữ mảnh chứa `lsu` — giữ nhầm mảnh `short-only` (chỉ chứa `Iris LSU`, không chứa thuật ngữ dài), bỏ sót `nguyen-nhan` (khớp `nguyên`) và `metadata-only` (khớp `Beam径` trong tên nguồn).
- Đây là lỗi sai chỗ lọc, không phải do test sai — nên không đổi kỳ vọng test.

## 2. Cách sửa

- Vị trí: `src/aios_habit/rag_v2/index.py`, hàm `_cjk_like_prefilter_ids`.
- Hướng đã chọn: **gộp thực thể với thuật ngữ rồi lấy 2 cụm dài nhất** (thay vì chỉ dùng thực thể). Thực thể vẫn được xét, nhưng nếu thực thể ngắn (như `lsu`) thì thuật ngữ dài hơn (`nguyên`, `beam径`) sẽ thắng một cách tự nhiên theo thứ tự độ dài.
- Lý do chọn: giữ đúng ý tưởng tốc độ của vé gốc (chỉ 1–2 cụm chọn lọc nhất), đồng thời sửa được cả hai chiều sai (bỏ sót + giữ nhầm). Không chọn hướng nới thành nhiều cụm hay quét đủ, vì sẽ làm mất tác dụng tăng tốc.
- Đánh đổi tốc độ: không đổi — vẫn tối đa 2 mệnh đề `LIKE ... OR ...` trong một câu `SQL`, cùng một lần quét chỉ mục. Với câu hỏi của vé, 2 cụm được chọn là `nguyên` và `beam径`, đủ giữ đúng 4 mảnh thật và loại 1 mảnh ngắn + 1 mảnh không liên quan.

## 3. Kiểm chứng bằng kiểm thử

- 2 test đích trong `tests/test_rag_v2_opt_pyloops.py`: `test_cjk_prefilter_matches_full_scan_on_long_term_queries`, `test_cjk_prefilter_drops_short_term_only_matches` — **2 passed** (0,5 giây).
- Hồi quy liên quan: `test_rag_v2_opt_pyloops.py` + `test_rag_v2_index.py` + `test_rag_v2_pipeline.py` — **79 passed** (7,03 giây).
- Không đổi hành vi ngoài tầng lọc sơ bộ; công tắc `AIOS_RAG_V2_CJK_PREFILTER=0` vẫn tắt được tầng này để về quét đủ khi cần.

## 4. Kiểm chứng bằng dùng thật

- Dựng chỉ mục tạm từ đúng bộ mảnh của kiểm thử, hỏi đúng câu hỏi của vé qua đường `search_with_summary` (đường truy vấn thật mà ứng dụng dùng):
  - Đường ứng viên: `deterministic_scan` (đường có lọc sơ bộ).
  - Thời gian hỏi đáp: khoảng **15,6 mili giây**.
  - Thứ tự mảnh trả về: `beam-ng`, `both`, `nguyen-nhan`, `metadata-only` (đủ 4 mảnh thật, không có `short-only`, không có `unrelated`).
- Không ghi chỉ mục thật, không đụng dữ liệu sản phẩm, không hợp nhất vào `main`.

## 5. Cổng repo

- Python `3.11.14` qua `uv`.
- `python -m compileall src tests`: sạch (`COMPILE_OK`).
- `python -m aios_habit.cli audit`: `{"status": "PASS"}`.
- `import aios_habit.workspace_chat_app`: thành công (`IMPORT_OK`).

## 6. Đề nghị

- Vé này chỉ sửa tầng lọc; mảnh nhiễu của bộ soạn (`synthesis.py`) vẫn chờ vé `SYNTH-COMPOSER-NOISE-FIX-HOME` như hàng chờ đã nêu.
