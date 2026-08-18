# Định Nghĩa Sẵn Sàng và Hoàn Thành (Definition of Ready and Done)

Status: `ACTIVE`
Owner role: Project owner / maintainer
Last reviewed: 2026-07-25
Review cadence: Every Gate Card opening and closure

## Sẵn Sàng (Ready)

Công việc ở trạng thái sẵn sàng (Ready) khi nó có: mục tiêu, các phi mục tiêu (non-goals), vai trò chủ sở hữu, phân loại quyền riêng tư, tác động kiến trúc/repository, tiêu chí nghiệm thu, các lệnh kiểm chứng, khái niệm hoàn tác (rollback) và các quyết định/phụ thuộc tường minh. Một hạng mục đã biết nhưng chưa mở gate thì phải giữ ở trạng thái `PLANNED`.

## Hoàn Thành (Done)

Công việc chỉ được coi là hoàn thành (Done) khi:

1. Danh sách cho phép (allowlist) của phạm vi được đáp ứng đầy đủ mà không kéo theo dọn dẹp ngoài lề;
2. Mã nguồn / kiểm thử / tài liệu đồng nhất và hiện hành;
3. Toàn bộ các cổng chất lượng đạt (PASS) kèm bằng chứng được ghi nhận;
4. Tính an toàn bảo mật / quyền riêng tư / dữ liệu riêng tư đã được xem xét;
5. Phương án hoàn tác và rủi ro tồn dư được nêu rõ ràng;
6. Roadmap, Handover và Changelog được cập nhật;
7. Quyết định của reviewer / chủ sở hữu bắt buộc đã được ghi nhận.

Chỉ số lượng bài test, tài liệu tự động sinh ra hoặc giao diện có vẻ chạy được đơn thuần không cấu thành trạng thái `DONE`.

