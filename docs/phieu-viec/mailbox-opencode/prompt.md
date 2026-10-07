# VÉ: INDEX-LOCALCOPY-FIX-HOME (loại bản sao chỉ mục cũ 28/09 khỏi mọi đường đọc mặc định)

- Mã vé: `INDEX-LOCALCOPY-FIX-HOME`
- Role gợi ý: DEFAULT (code nhỏ + test)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/index-localcopy-fix-home.md`
- Căn cứ: báo cáo `index-localcopy-check-home.md` (ĐẠT 08/10) — bản sao `local_runs/workspace_chat_rag_v2_production/.../library.sqlite` là bản ghim cũ 28/09 (496 tài liệu / 133.144 mảnh, thiếu 393 tài liệu / 16.656 mảnh so với production 889 / 149.800). App thật an toàn (đọc production ở ổ C), nhưng 3 đường mặc định còn trỏ vào bản cũ. Điều phối DUYỆT hướng (b) của báo cáo: sửa đường mặc định, KHÔNG làm tươi bản sao, KHÔNG xoá bản sao ở vé này.

## Việc phải làm (đúng 3 điểm đã rà)

1. `scripts/workspace_chat_rag_v2_activation.py:54` — `DEFAULT_RUNTIME_ROOT` đang trỏ `local_runs/workspace_chat_rag_v2_production`: đổi hành vi để khi không truyền `--runtime-root` thì dùng đường production thật ở ổ C (theo config `config/workspace_chat_rag_v2.local.json`) hoặc dừng với thông báo rõ ràng bằng tiếng Việt nếu không xác định được — tuyệt đối không lặng lẽ dùng bản cũ trong `local_runs`.
2. `scripts/benchmark_adaptive_reranking.py:593` — fallback `PROJECT_ROOT / "local_runs/workspace_chat_rag_v2_production"` khi thiếu `runtime_root`/`deployment`: xử lý cùng nguyên tắc như điểm 1 (trỏ production thật hoặc dừng rõ ràng).
3. `tests/test_index_status.py` (`test_index_status_matches_real_db_if_present`) — bài kiểm đang đọc bản trong `local_runs` rồi khẳng định số production (149.800/889) nên đỏ oan và gây hiểu nhầm production hỏng: sửa để bài kiểm hoặc (a) đọc đúng tệp production theo config và bỏ qua sạch khi tệp không tồn tại, hoặc (b) nếu vẫn đọc bản local thì khẳng định đúng tính chất "bản cũ" của nó. Chọn một hướng, ghi lý do trong báo cáo. Không nới test vô căn cứ.

## Kiểm chứng

- Chạy lại `tests/test_index_status.py` trên máy nhà: xanh (hoặc skip có lý do rõ in ra).
- Chạy thử 2 script ở chế độ an toàn (dry-run/help nếu có) để chứng minh mặc định mới không còn trỏ `local_runs`.
- Cổng repo: Python 3.11, compileall, `cli audit`, import app; không hồi quy các suite chạm tới.

## Rào cứng

- Không xoá/di chuyển/đổi tên bản sao cũ; không đụng tệp production; không ghi index; không merge `main`.
