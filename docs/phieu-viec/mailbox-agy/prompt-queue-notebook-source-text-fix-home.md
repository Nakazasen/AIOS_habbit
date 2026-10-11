# Vé NOTEBOOK-SOURCE-TEXT-FIX-HOME (agy, máy nhà) — sửa crash AttributeError khi hỏi trong sổ tay có gắn nguồn

**Nguồn gốc:** thợ desktop phát hiện khi nghiệm thu `DESKTOP-BLOCK-SMOKE-HOME` (2026-10-11), điều phối đã rà mã xác nhận: hàm `get_workspace_chat_preparation_summary` trong `src/aios_habit/workspace_chat_rag_v2_adapter.py` (khai báo ~dòng 1930) truy cập thuộc tính `.text` trên MỌI nguồn ngữ cảnh (`sources = tuple(s for s in context_sources if (s.text or "").strip())`). Đối tượng `NotebookSource` lưu trong SQLite store KHÔNG có thuộc tính `.text` (khác `ContextSource`) → `AttributeError: 'NotebookSource' object has no attribute 'text'` làm đứt luồng xử lý câu hỏi trong các sổ tay có gắn danh sách NotebookSource.

## Việc phải làm
1. Tái hiện bằng một ca kiểm thử mang đối tượng dạng NotebookSource (không có `.text`) đi qua hàm trên — phải crash trước sửa, qua sau sửa.
2. Sửa tại điểm chạm: chuẩn hoá truy cập văn bản của nguồn (hoặc bổ sung thuộc tính tương đương cho NotebookSource ở nơi sinh đối tượng — chọn điểm sửa ít lan nhất và ghi lý do trong báo cáo). Hành vi với ContextSource hiện nay không đổi.
3. Đủ 4 cổng chất lượng của repo (compileall, pytest liên quan, cli audit, import app); rà thêm các điểm khác trong cùng adapter cũng giả định nguồn luôn có `.text` và ghi kết quả rà vào báo cáo (sửa luôn nếu cùng một điểm chạm, ngoài phạm vi thì chỉ ghi nhận).
Báo cáo tại `docs/phieu-viec/ket-qua/notebook-source-text-fix-home.md`. KHÔNG đụng chỉ mục production.
