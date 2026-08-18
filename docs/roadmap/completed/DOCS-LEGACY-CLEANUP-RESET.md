# Dọn Dẹp và Đặt Lại Tài Liệu Kế Thừa (DOCS-LEGACY-CLEANUP-RESET)

Status: `DONE`

## Mục Tiêu (Goal)

Thay thế các tài liệu hướng dẫn mâu thuẫn hiện tại, tạo một nguồn lộ trình canonical duy nhất và phân loại bằng chứng lịch sử mà không làm mất tính truy xuất nguồn gốc.

## Trong Phạm Vi (In Scope)

- `README.md`, `PROJECT_HANDOVER.md`, `WORKLENS_ARCHITECTURE.md`
- Các sổ tay runbook cài đặt / vận hành / phát triển
- `ROADMAP.md` chuẩn tắc canonical, chuyển hướng từ lộ trình tổng cũ đã khai tử
- Quy ước Thẻ Cổng (Gate Card), chính sách lưu trữ archive và manifest khai tử
- Lưu trữ các bằng chứng thiết kế / UX cũ mà không chỉnh sửa các tuyên bố lịch sử của chúng

## Các Phi Mục Tiêu (Non-goals)

- Không triển khai tính năng runtime RAG.
- Không xóa service / monolith Case Cockpit.
- Không di chuyển dữ liệu riêng tư / runtime.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

1. Tài liệu người dùng thông thường chỉ định Workspace Chat là giao diện duy nhất được hỗ trợ.
2. Một lộ trình canonical duy nhất xác định rõ trạng thái active / planned / retired.
3. Các Gate Card phân biệt rõ ràng công việc đang hoạt động với bằng chứng kiểm toán lịch sử.
4. Tài liệu được chuẩn bị chứa các tuyên bố cũ được bảo tồn dưới dạng lưu trữ archive, không commit dưới dạng sự thật kiến trúc / lộ trình hiện tại.

## Bằng Chứng Kiểm Chứng (Verification Evidence)

Đã kiểm chứng vào ngày 2026-07-25:

- Commit triển khai: `9123caa` (`Clean legacy routes and reset project documentation`).
- Biên dịch: passed.
- Toàn bộ pytest: `892 passed`.
- Kiểm toán CLI audit: passed.
- Các fixture mẫu secret có chủ đích được xây dựng lúc runtime, bảo toàn độ bao phủ của bộ phát hiện mà không lưu trữ các chuỗi credential giả mạo hoàn chỉnh trong mã nguồn.
- `git diff --check`: passed trước khi đóng cổng.

## Hoàn Tác (Rollback)

Tất cả các thay đổi đều là thay đổi tài liệu / đường dẫn. Khôi phục các tệp được chỉ định hoặc di chuyển lưu trữ từ Git nếu cần khôi phục lại tham chiếu.

