# Danh Mục Thu Hồi Thành Phần Cũ (Legacy Retirement Manifest)

## Ranh Giới (Boundary)

Workspace Chat là giao diện người dùng chính (primary UI). Mã nguồn cũ không được xem là tuyến người dùng được hỗ trợ.
Dữ liệu runtime `local_cases/` và `local_runs/` không thuộc mã nguồn dọn dẹp và phải tiếp tục bị Git bỏ qua (Git ignored).

## Danh Mục (Inventory)

| Mục (Item) | Phân loại (Classification) | Hành động (Action) | Bằng chứng / hoàn tác (Evidence / rollback) |
|---|---|---|---|
| `studio.py` | `RETIRE` | Xóa cùng với tuyến console/tài liệu/kiểm thử chỉ dành riêng cho Studio | Không tìm thấy lệnh import sản xuất nào; khôi phục từ Git nếu cần |
| `RUN_AIOS_HABIT_STUDIO.bat`, `scripts/run_studio.ps1` | `RETIRE` | Xóa sau khi trình khởi chạy Workspace Chat được xác minh | Chỉ tạo lại từ lịch sử Git nếu được yêu cầu |
| `aios-habit-studio` | `RETIRE` | Xóa mục gói | Tuyến duy nhất trong `pyproject.toml` |
| `RUN_AIOS_CASE_COCKPIT.bat`, `scripts/run_case_cockpit.ps1` | `RETIRE` | Xóa các tuyến trực tiếp công khai | Mã nguồn Case được giữ lại chờ lát cắt tiếp theo |
| `aios-case-cockpit` | `RETIRE` | Xóa mục gói | Mã nguồn Case được giữ lại chờ lát cắt tiếp theo |
| `case_cockpit.py` | `RETIRE_AFTER_CURRENT_VALIDATION` | Đã xóa trong worktree hiện tại; giữ đường dẫn hoàn tác Git cho đến khi xác thực/commit đầy đủ | Các dịch vụ dùng chung vẫn có caller trực tiếp và nằm ngoài đợt xóa này |
| `case_*`, sơ đồ trực quan, dịch vụ handoff | `AUDIT_REQUIRED` | Giữ cho đến khi ma trận phụ thuộc/khả năng được phê duyệt | Một số module/kiểm thử không thuộc cockpit vẫn import chúng |
| `mom_*` pilot | `KEEP_ISOLATED` | Giữ làm điểm đo chuẩn/tham chiếu cho đến khi đánh giá RAG v2 thay thế nó | Không có phụ thuộc lõi RAG v2 |

## Tiêu Chí Hoàn Thành Cho Lát Cắt Tuyến Công Khai / Studio (Completion criteria for the Studio/public-route slice)

1. Chỉ các trình khởi chạy Workspace Chat được ghi nhận trong tài liệu và kiểm thử.
2. Không có tập lệnh console công khai nào tham chiếu đến Studio hoặc Case Cockpit.
3. Không có tài liệu README/cài đặt/vận hành đang hoạt động nào hướng dẫn người dùng đến thành phần cũ.
4. `studio.py` và tài liệu/kiểm thử chỉ dành cho Studio đã bị loại bỏ.
5. Vượt qua toàn bộ kiểm thử/biên dịch/kiểm toán; các tệp runtime bị bỏ qua vẫn nguyên vẹn.
6. Bằng chứng worktree hiện tại được ghi lại trong lộ trình/nhật ký thay đổi/bàn giao trước khi đánh dấu việc thu hồi là `DONE`.

