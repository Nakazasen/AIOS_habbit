# Di Chuyển Phụ Thuộc và Khai Tử Case Cockpit (CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT)

Status: `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE — 2026-08-16`

## Mục Tiêu (Goal)

Tạo ma trận phụ thuộc / năng lực chính xác cần thiết để khai tử khối nguyên khối (monolith) Case Cockpit một cách an toàn, tách rời các tiện ích dùng chung và loại bỏ mã chết (dead code) của cockpit cũ.

## Các Hành Động Đã Hoàn Thành (Completed Actions)

1. Tiến hành kiểm toán phụ thuộc xuyên suốt `src/` và `tests/`.
2. Chứng minh không có bất kỳ lệnh import nào từ `case_cockpit.py` trong `workspace_chat_*` và `rag_v2/*`.
3. Nhúng trực tiếp (inline) `safe_asset_filename` vào `source_ingest.py` và các hàm trợ giúp `_ingest_*` vào `case_store.py`.
4. Loại bỏ các tệp nguyên khối đã chết:
   - `src/aios_habit/case_cockpit.py` (171 KB)
   - `src/aios_habit/case_actions.py`
   - `src/aios_habit/case_graph.py`
   - `src/aios_habit/case_handover.py`
   - `src/aios_habit/case_ingest.py`
   - Các tệp kiểm thử UI cockpit lỗi thời.
5. Bằng chứng chất lượng tập trung / toàn bộ hiện tại bắt buộc phải được chạy lại sau khi cây làm việc kết hợp cuối cùng được dàn dựng. Các dịch vụ `case_store` dùng chung vẫn đang được sử dụng và nằm ngoài phạm vi xóa tệp monolith.

