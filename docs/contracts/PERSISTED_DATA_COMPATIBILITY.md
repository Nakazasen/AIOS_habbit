# Khả Năng Tương Thích Dữ Liệu Lưu Trữ

Trạng thái: `HOÀN TẤT MỘT PHẦN`
Vai trò chủ sở hữu: Chủ sở hữu dự án / Người rà soát lưu trữ
Xem xét lần cuối: 2026-09-09
Chu kỳ xem xét: Trước khi thay đổi mô hình lưu trữ, trường JSONL hoặc lược đồ SQLite

## Các hình thức lưu trữ hiện tại

| Kho lưu trữ | Vị trí / Định dạng | Tuyên bố tương thích |
|---|---|---|
| Trạng thái Workspace Chat | JSONL (được gitignore) dưới `local_cases/workspace_chat/` | Triển khai cục bộ dựa trên mô hình; hiện chưa công bố API/phiên bản ổn định ra bên ngoài |
| Chỉ mục RAG v2 | Bảng `chunks` trong SQLite tại đường dẫn do bên gọi chọn | Tạo lược đồ có tính bất biến lặp (idempotent) cho các trường hiện tại; kiểm tra tính toàn vẹn khi khởi tạo |
| Hồ sơ vụ việc | `local_cases/workspace_cases.sqlite` | Lược đồ có `PRAGMA user_version`, bảng lịch sử di chuyển phiên bản (migration), sao lưu trực tuyến (Online Backup) trước thay đổi và hoàn tác khi lỗi; cấm lưu bản chép lời thô |
| Dự đoán cục bộ | `production_prediction.sqlite` trong thư mục chạy cục bộ | Đã triển khai; quản lý bằng các bước di chuyển phiên bản có kiểm tra toàn vẹn, lưu trữ bất biến lặp các dự đoán, kết quả đo độ lệch (drift) và phiên chạy ngầm (shadow mode) |
| Runtime Bằng chứng / Bộ nhớ | Các đường dẫn JSONL (được gitignore) | Quản trị bởi các lược đồ dữ liệu; dữ liệu cục bộ của người dùng luôn nằm ngoài Git |
| Siêu dữ liệu Bản dựng / Phát hành | `pyproject.toml` và tài liệu được theo dõi | Phiên bản là siêu dữ liệu của gói phần mềm, không phải phiên bản di chuyển dữ liệu chạy thực tế |

## Quy tắc Tương thích

1. Các thay đổi thêm trường mới (additive) bắt buộc phải có giá trị mặc định và bài kiểm thử cho dữ liệu cũ/chưa biết khi các mô hình hỗ trợ.
2. Việc đổi tên/xóa bỏ mang tính phá hủy cần có quy trình sao lưu, kế hoạch di chuyển, phương án hoàn tác và ghi chú phát hành trước khi triển khai.
3. Các thay đổi trong SQLite cần cơ chế phát hiện/đánh số phiên bản di chuyển trước khi tuyên bố tương thích tại chỗ.
4. Sự cố hỏng kho dữ liệu phải được xử lý như một sự kiện khôi phục vận hành, tuyệt đối không giấu lỗi bằng cách âm thầm xóa dữ liệu của người dùng.
5. Di chuyển phiên bản kho hồ sơ phải kiểm tra phiên bản/mã băm liên tục, `quick_check` trước và sau, tạo bản sao lưu trước thay đổi, phục hồi bản sao lưu nếu lỗi và không để lại tệp WAL/SHM không nhất quán.
6. Hoạt động, đánh giá, phê duyệt và bằng chứng bổ sung là hình thức chỉ ghi thêm (append-only) hoặc đánh phiên bản; nghiêm cấm thay đổi phá hủy lịch sử.

## Các Giới hạn Hiện tại

Tự động di chuyển lược đồ từ xa, đồng bộ đa thiết bị và khả năng tương thích ngược chính thức hiện chưa phải là các tuyên bố đã triển khai. Xem [Khả năng tương thích di chuyển dữ liệu](../operations/DATA_MIGRATION_COMPATIBILITY.md).

## Các Bản ghi Liên quan

- [ADR-0003](../adr/0003-local-sqlite-lexical-index.md)
- [Sao lưu và phục hồi](../operations/BACKUP_RESTORE.md)
