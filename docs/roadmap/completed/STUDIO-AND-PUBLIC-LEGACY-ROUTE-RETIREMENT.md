# Khai Tử Tuyến Kế Thừa Công Khai và Studio (STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT)

Status: `DONE`

## Mục Tiêu (Goal)

Loại bỏ các đường dẫn thực thi công khai tới Studio / Case Cockpit cũ và đảm bảo tên gọi launcher của Workspace Chat là trung thực.

## Phạm Vi (Scope)

- Bổ sung `RUN_AIOS_WORKSPACE_CHAT.bat` và `scripts/run_workspace_chat.ps1`.
- Loại bỏ các tuyến console trong package cho Studio và Case Cockpit.
- Loại bỏ mã nguồn Studio và các bài kiểm thử / tài liệu chỉ dành riêng cho Studio.
- Loại bỏ các script khởi chạy trực tiếp Case Cockpit và các kiểm tra chỉ dành riêng cho tuyến đó.
- Giữ lại mã nguồn Case Cockpit / các dịch vụ dùng chung cho lát cắt khai tử được kiểm toán tiếp theo.

## Các Phi Mục Tiêu (Non-goals)

- Không xóa `case_cockpit.py` trong cổng này.
- Không xóa bất kỳ dịch vụ `case_*`, map, handoff, router hay MOM nào chỉ vì nó từng được sử dụng bởi một giao diện cũ.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

1. Tài liệu README / cài đặt / vận hành chỉ trỏ tới các launcher của Workspace Chat.
2. Các script của package không để lộ bất kỳ lệnh Studio / Cockpit nào.
3. Không còn module Studio, launcher Studio cũ hoặc launcher Case Cockpit trực tiếp nào tồn tại.
4. Kiểm thử hồi quy ranh giới Workspace Chat thành công.
5. Toàn bộ kiểm thử, biên dịch và kiểm toán CLI audit đều đạt; các tài sản runtime bị bỏ qua giữ nguyên vẹn.

## Bằng Chứng Kiểm Chứng (Verification Evidence)

Đã kiểm chứng vào ngày 2026-07-25:

- Commit triển khai: `9123caa` (`Clean legacy routes and reset project documentation`).
- Mã nguồn Studio, launcher cũ và các tuyến package đã bị loại bỏ.
- Launcher Workspace Chat và kiểm thử hồi quy ranh giới đã sẵn sàng.
- Biên dịch: passed.
- Toàn bộ pytest: `892 passed`.
- Kiểm toán CLI audit: passed.
- Các tài sản runtime bị bỏ qua và các dịch vụ dùng chung của Case Cockpit vẫn giữ nguyên vẹn.
- `git diff --check`: passed trước khi đóng cổng.

## Hoàn Tác (Rollback)

Git có thể khôi phục lại module / launcher đã bị loại bỏ. Không có dữ liệu runtime cục bộ nào bị thay đổi.

