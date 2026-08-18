# Khả Năng Tương Thích và Di Chuyển Dữ Liệu (Data Migration and Compatibility)

Status: `PROPOSED`
Owner role: Project owner / storage reviewer
Last reviewed: 2026-07-25
Review cadence: Before any persisted-data schema migration

## Phạm vi (Scope)

Tài liệu này quản trị tính tương thích của tệp JSONL Workspace Chat và chỉ mục RAG. Nó tách biệt với tệp `MIGRATION_POLICY.md` ở thư mục gốc (vốn quản trị việc thu hoạch mã nguồn/tính năng từ các repository khác).

## Trạng thái Hiện tại (Current State)

Hiện tại chưa có framework di chuyển tự động nào được triển khai hoặc đánh dấu phiên bản schema bền vững cho Workspace Chat JSONL / RAG SQLite. Do đó, việc di chuyển tại chỗ (in-place migration), tương thích ngược (backward compatibility) và hạ cấp (downgrade) hiện chưa phải là các cam kết bảo đảm.

## Kế hoạch Di chuyển Bắt buộc (Required Migration Plan)

Trước khi thay đổi các trường dữ liệu / bảng lưu trữ bền vững:

1. Gán một ID di chuyển và nêu rõ phiên bản nguồn / phiên bản đích.
2. Kiểm kê các kho lưu trữ bị ảnh hưởng và phân loại các trường: thêm mới (additive), chuyển đổi (transformed) hoặc phá hủy (destructive).
3. Sao lưu dữ liệu của chủ sở hữu và chứng minh khả năng khôi phục trên dữ liệu tổng hợp trước.
4. Xác định tính idempotent, kỳ vọng về transaction/tính nguyên tử (atomicity) và hành vi khi thất bại một phần.
5. Xác định đường dẫn tiến tới, đường dẫn hoàn tác (rollback) và thông điệp an toàn hiển thị cho người dùng.
6. Thêm các bài kiểm thử fixture cũ/mới và kiểm thử khởi tạo kho lưu trữ sạch.
7. Ghi lại ghi chú phát hành và cửa sổ tương thích.

## Quy tắc An toàn (Safety Rules)

- Tuyệt đối không âm thầm xóa dữ liệu lỗi định dạng/riêng tư chỉ để ứng dụng khởi động thành công.
- Tuyệt đối không chạy logic di chuyển dữ liệu từ tuyến provider hoặc CI đối với dữ liệu của chủ sở hữu.
- Bất kỳ thay đổi schema nào thiếu bằng chứng di chuyển dữ liệu đều là một lỗi chặn phát hành (release blocker).

## Các Bản ghi Liên quan (Related Records)

- [Khả năng tương thích dữ liệu lưu trữ (Persisted-data compatibility)](../contracts/PERSISTED_DATA_COMPATIBILITY.md)
- [Sao lưu và phục hồi (Backup and restore)](BACKUP_RESTORE.md)
- [Danh mục kiểm tra phát hành (Release checklist)](../release/RELEASE_CHECKLIST.md)

