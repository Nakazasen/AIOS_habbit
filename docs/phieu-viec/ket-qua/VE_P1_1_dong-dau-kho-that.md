# Báo cáo Vé P1.1 — dừng an toàn khi chưa xác định kho production

## Kết quả

**Chưa đóng dấu. Dừng ở bước 1: chưa xác định được kho production.** Cấu hình collection `tri_thuc` tìm thấy trên ổ C có `storage_root` rỗng; chưa có bằng chứng để xác định thư mục runtime production đang được ứng dụng sử dụng. Không sao lưu, không chép đè, không chuyển ứng dụng và không chạy B1–B5. Không ghi vào bất kỳ tệp chỉ mục nào.

## Máy và phạm vi

- Máy: `h410asrock`.
- Nhánh: `phieu-viec/rag-fix1`.
- Thời điểm kiểm tra: 2026-09-28 05:17 giờ `+07`.
- Các lượt dò cấu hình, tiến trình và tệp chỉ mục trên ổ C chỉ đọc. Không sửa dữ liệu trong `local_cases/`, không sao lưu hoặc thay tệp SQLite, không ghi dữ liệu RAG lên ổ D.

## Bằng chứng xác định đường dẫn

- File cấu hình tìm thấy: `C:\c\AIOS_ve03_worktree\local_cases\workspace_chat\collections.jsonl`. Bản ghi collection `tri_thuc` có `storage_root` rỗng.
- Dò trên ổ C, trong các thư mục đọc được, chỉ tìm thấy file `library.sqlite` tại `C:\AIOS_habit_index_ve03\library.sqlite` (2.552.659.968 byte). Đây là kho canary đã nêu trong vé, không có bằng chứng cho thấy nó là kho production.
- Không tìm thấy tệp `library.sqlite` khác trong lượt dò. Các lỗi truy cập thư mục bị bỏ qua bởi lệnh dò; vì vậy kết quả này không chứng minh rằng mọi thư mục trên ổ C đều đã đọc được.
- Không có tiến trình Streamlit đang chạy để mở giao diện và xác nhận đường dẫn. Các tiến trình Python quan sát được chạy `antigravity_sidecar_daemon.py` và `custom_harness.mcp_server`.

Vì `storage_root` rỗng, đường dẫn thư viện phụ thuộc vào thư mục runtime/profile mà ứng dụng production đang dùng. Lượt kiểm tra này không xác định được profile đó. Không suy đoán đường dẫn hoặc coi kho canary là production.

## Trạng thái các bước

| Bước | Kết quả | Lý do |
| --- | --- | --- |
| 1. Xác định `storage_root` và đường dẫn production | Chưa đạt | `storage_root` rỗng; chưa xác định được runtime/profile production. |
| 2. Kiểm nhanh canary trước khi sao chép | Chưa chạy | Dừng theo điều kiện fail-closed ở bước 1. |
| 3. Sao lưu production và kiểm toàn vẹn | Chưa chạy | Chưa xác định được tệp production. |
| 4. Chép canary và so SHA-256 + kích thước | Chưa chạy | Không có đích đã xác thực. |
| 5. Chạy B1–B5 và đóng dấu | Chưa chạy | Không thay kho hoặc chuyển ứng dụng. |

## Cần xác nhận để tiếp tục

Cần Muse/chủ sở hữu cung cấp đường dẫn đầy đủ trên ổ C của kho `library.sqlite` production và bằng chứng xác nhận đường dẫn đó (giao diện app hoặc cấu hình collection/runtime đang được app production dùng). Nếu `storage_root` vẫn rỗng, cần xác nhận rõ runtime root và profile production. Chưa có xác nhận này thì không sao lưu hoặc ghi vào chỉ mục.