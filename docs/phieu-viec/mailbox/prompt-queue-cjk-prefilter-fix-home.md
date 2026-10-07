# VÉ XẾP HÀNG: CJK-PREFILTER-FIX-HOME (sửa lọc sơ bộ CJK giữ sai mảnh — 2 test đỏ đã truy vết)

- Mã vé: `CJK-PREFILTER-FIX-HOME`
- Role gợi ý: DEFAULT (code + test)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/cjk-prefilter-fix-home.md`
- Căn cứ: báo cáo `test-red22-fix-home.md` mục 2 — đã truy vết gốc: với câu truy vấn của 2 test, `extract_content_terms` cho `entities=('lsu',)` nên tầng lọc sơ bộ chỉ giữ mảnh chứa `lsu`: giữ nhầm mảnh short-only, bỏ sót mảnh nguyen-nhan/metadata-only. Điểm sửa: `src/aios_habit/rag_v2/index.py` (`_extract_query_entities` / `_cjk_like_prefilter_ids`). Vé trước cấm đụng file này vì vé khác đang dùng; khi vé này được phát hành thì điều phối đã xác nhận file trống.

## Việc phải làm

1. Sửa tầng lọc sơ bộ để không rớt mảnh liên quan khi thực thể trích được quá hẹp (hướng gợi ý từ truy vết: mở rộng tập thực thể/thuật ngữ cho prefilter hoặc cho prefilter nới điều kiện khi số thực thể ít — chọn hướng theo code thực tế, ghi rõ lý do + đánh đổi tốc độ trong báo cáo; prefilter là đường TỐC ĐỘ nên không được biến nó thành quét đủ trá hình).
2. 2 test đích phải xanh: `test_cjk_prefilter_matches_full_scan_on_long_term_queries`, `test_cjk_prefilter_drops_short_term_only_matches` (tests/test_rag_v2_opt_pyloops.py). Nếu kết luận kỳ vọng test cần đổi theo đánh đổi đã duyệt thì ghi rõ căn cứ — cấm nới test im lặng.
3. Không hồi quy: suites rag_v2 liên quan (index, pipeline, pyloops) + cổng repo (Python 3.11, compileall, cli audit, import app).

## Rào cứng

- Không ghi index thật (chỉ test trên fixture/index tạm); không đổi hành vi ngoài tầng prefilter; không merge `main`.
