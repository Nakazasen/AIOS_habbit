# Khả Năng Tương Thích Dữ Liệu Lưu Trữ (Persisted Data Compatibility)

Status: `PARTIAL`
Owner role: Project owner / storage reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing persisted models, JSONL fields or SQLite schema

## Các hình thức lưu trữ hiện tại (Current Persistent Forms)

| Kho lưu trữ | Vị trí / Định dạng | Tuyên bố tương thích |
|---|---|---|
| Trạng thái Workspace Chat | JSONL (được gitignore) dưới `local_cases/workspace_chat/` | Triển khai cục bộ dựa trên model; hiện chưa công bố API/phiên bản ổn định ra bên ngoài |
| Chỉ mục RAG v2 | Bảng `chunks` trong SQLite tại đường dẫn do caller chọn | Tạo schema có tính idempotent cho các trường hiện tại; chưa có framework di chuyển phiên bản schema tường minh |
| Hồ sơ vụ việc | `local_cases/workspace_cases.sqlite` | Schema có `PRAGMA user_version`, bảng lịch sử migration, Online Backup trước thay đổi và rollback khi lỗi; raw chat/excerpt bị cấm |
| Dự đoán cục bộ | `production_prediction.sqlite` trong runtime root cục bộ | Chưa triển khai; khi mở phải có version/digest và outbox idempotent sang kho case |
| Runtime Bằng chứng / Bộ nhớ | Các đường dẫn JSONL (được gitignore) | Quản trị bởi các schema; dữ liệu cục bộ của chủ sở hữu luôn nằm ngoài Git |
| Metadata Build / Phát hành | `pyproject.toml` và tài liệu được theo dõi | Version là metadata của package, không phải phiên bản di chuyển dữ liệu runtime |

## Quy tắc Tương thích (Compatibility Rules)

1. Các thay đổi thêm trường mới (additive) bắt buộc phải có giá trị mặc định (default) và bài test cho dữ liệu cũ/chưa biết khi các model hỗ trợ.
2. Việc đổi tên/xóa bỏ mang tính phá hủy (destructive) cần có quy trình sao lưu, kế hoạch di chuyển, phương án hoàn tác và ghi chú phát hành trước khi triển khai.
3. Các thay đổi trong SQLite cần cơ chế phát hiện/đánh số phiên bản di chuyển trước khi tuyên bố tương thích tại chỗ (in-place compatibility).
4. Sự cố hỏng kho dữ liệu phải được xử lý như một sự kiện khôi phục vận hành, tuyệt đối không giấu lỗi bằng cách âm thầm xóa dữ liệu của chủ sở hữu.
5. Migration kho case phải kiểm tra version/checksum liên tục, `quick_check` trước và sau, tạo snapshot trước thay đổi, phục hồi snapshot nếu lỗi và không để lại WAL/SHM không nhất quán.
6. Activity, review, approval và evidence bổ sung là append-only hoặc versioned; thay đổi phá hủy lịch sử bị cấm.

## Các Giới hạn Hiện tại (Current Limits)

Tự động di chuyển schema, đồng bộ đa thiết bị và khả năng tương thích ngược chính thức hiện chưa phải là các tuyên bố đã triển khai. Xem [Khả năng tương thích di chuyển dữ liệu (Data migration compatibility)](../operations/DATA_MIGRATION_COMPATIBILITY.md).

## Các Bản ghi Liên quan (Related Records)

- [ADR-0003](../adr/0003-local-sqlite-lexical-index.md)
- [Sao lưu và phục hồi (Backup and restore)](../operations/BACKUP_RESTORE.md)
