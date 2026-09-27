# Báo cáo Vé P1 — dừng an toàn trước khi sao lưu kho production

## Kết quả

**Chưa đóng dấu. Dừng sau Bước 1.** Kho canary đạt các dấu toàn vẹn đã yêu cầu. Không xác định được tệp kho production trên ổ C, vì vậy không sao lưu, không chép đè, không chuyển ứng dụng sang kho mới và không chạy B1–B5. Không có cơ sở để đóng dấu kho chạy thật.

## Máy và phạm vi

- Máy: `h410asrock`.
- Nhánh: `phieu-viec/rag-fix1`; `HEAD` tại thời điểm báo cáo: `d74d5e7` (commit ghi tiến độ, không chứa thay đổi mã nguồn).
- Python: `3.11.14`.
- Thời điểm kiểm tra: 2026-09-28 khoảng 04:58–05:05 giờ `+07`.
- Mọi thao tác với dữ liệu chỉ đọc trên ổ C. Không ghi, sao lưu hay sao chép tệp chỉ mục; không ghi ổ D; không sửa mã nguồn hoặc kiểm thử.

## Bước 1 — kiểm kho canary

Tệp `C:\AIOS_habit_index_ve03\library.sqlite`, kích thước quan sát được `2.552.659.968` byte. Mở SQLite bằng chế độ chỉ đọc (`mode=ro`).

- `PRAGMA integrity_check`: `ok`.
- Số khối có thể truy xuất: `107.331`.
- Vector ONNX dense: `107.331`; dấu vân tay `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`.
- Vector ONNX sparse: `107.331`, cùng dấu vân tay trên.
- Đang chờ: dense `0`, sparse `0`.
- Vector cũ mang dấu vân tay PyTorch `ce7fb53f797f0973e2cbf51d6a6ffef4de9a32b659b979f45663c6c360c8e43c`: `340` dense và `340` sparse; được giữ nguyên.

**Bước 1 đạt.**

## Đường dẫn kho production đã dò

Dò tệp tên `workspace_chat.sqlite` đệ quy trên ổ C. Kết quả đọc được có một tệp mang tên đó: `C:\c\AIOS_ve03_worktree\local_runs\workspace_chat_rag_v2_canary\workspace_chat.sqlite` (`16.384` byte). Tệp này nằm trong thư mục `canary`, không phải đường dẫn kho production mà vé yêu cầu. Không thấy tệp `workspace_chat_rag_v2_production\workspace_chat.sqlite` trên các thư mục ổ C đọc được. Lượt dò toàn ổ gặp một số thư mục hệ thống từ chối quyền truy cập.

Tôi không suy đoán tệp `canary` là production và không tìm/ghi sang ổ D.

## Các bước còn lại

| Bước | Kết quả | Lý do |
| --- | --- | --- |
| 2. Sao lưu production hiện tại và kiểm toàn vẹn bản sao lưu | Chưa chạy | Chưa xác định được đúng tệp production trên ổ C. |
| 3. Chép canary và so kích thước + SHA-256 | Chưa chạy | Không có đích production đã xác nhận; không chép tệp. |
| 4. Chạy B1–B5 trên kho mới | Chưa chạy | Không chuyển ứng dụng sang kho chưa được xác định. |
| 5. Đóng dấu kho thật | Không đạt điều kiện | Chưa có bản sao, SHA-256 sau chép hoặc kết quả B1–B5. |

Không lập SHA-256 cho bản sao lưu hoặc kho mới vì hai thao tác này chưa diễn ra. Không tạo backup giả để thay cho backup production.

## Cần Muse xác nhận

Vui lòng ghi rõ đường dẫn đầy đủ trên ổ C của tệp production `workspace_chat.sqlite` mà ứng dụng đang đọc trên máy `h410asrock`, hoặc xác nhận cần dừng Vé P1 nếu kho production không nằm trên ổ C. Chưa có xác nhận này thì không thực hiện Bước 2–5.
