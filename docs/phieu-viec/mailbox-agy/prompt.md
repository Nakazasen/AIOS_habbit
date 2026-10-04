# Ticket: DON-O-C-AGY — Dọn ổ C máy nhà (user đã cho phép 2026-09-29 ~20:10 +07)

## Bối cảnh
Ổ C máy nhà vừa được dọn khẩn cấp ~1.4GB (lúc cứu opencode 22:00), giờ còn trống
khoảng 2.9GB — vẫn quá ít. User cho phép dọn sâu, mục tiêu lấy lại thêm ~5–8GB.
Thợ agy làm vé này (việc nhẹ, đọc/liệt kê/xóa có kiểm chứng — đúng thế mạnh agy).

## Các bước (làm theo đúng thứ tự, dừng ngay nếu bước nào không chắc chắn)

### Bước 0: Kiểm tra đối tượng mới phình (user đã duyệt dọn, từ tổng kết cứu opencode 22:00)
- `opencode state` ~434MB (`C:\Users\Admin\AppData\Local\Temp\opencode` hoặc thư mục state opencode) — CHỈ xóa session state cũ, GIỮ session đang chạy của opencode hiện tại.
- `.codex` ~4.9GB, `.gemini` ~7.7GB — liệt kê, xác minh là cache/log cũ không cần thiết, không xóa config đang dùng.
- Với mỗi mục: liệt kê nội dung → xác minh an toàn → xóa → báo dung lượng.

### Bước 1: Rác tmp (an toàn nhất)
- Quét `C:\Windows\Temp`, `%TEMP%`, `local_runs\**\tmp`, `scratch\` các file
  quá 7 ngày không đụng tới.
- Chỉ xóa file tmp/log/cache. KHÔNG xóa file đang mở/lock (đặc biệt: opencode
  đang chạy — không đụng session/state của nó).

### Bước 2: venv trùng lặp
- Liệt kê tất cả venv (`venv`, `.venv`, `env*`) trong `D:\Sandbox\AIOS_habbit` và ổ C.
- Giữ lại 1 venv đang dùng. Xóa venv trùng không dùng (so `pip freeze` trước).

### Bước 3: Worktree vé 0.3
- Vé 0.3 đã đóng. Nếu worktree còn tồn tại: xác nhận mọi commit đã push/merge,
  rồi `git worktree remove`.

### Bước 4: 2 backup cũ (CẦN XÁC MINH TRƯỚC KHI XÓA)
- Liệt kê backup index trên ổ C.
- Với mỗi backup định xóa: chạy `PRAGMA integrity_check` trên bản GIỮ LẠI,
  phải trả về `ok` mới được xóa bản cũ.
- KHÔNG xóa nếu chỉ còn 1 bản backup duy nhất của index production.

### Bước 5: tri_thuc — CHƯA LÀM (chờ E2v3 đóng hẳn)
- Bỏ qua bước này trong vé hiện tại.

## Cấm tuyệt đối
- Không xóa index production đang dùng (`workspace_chat_rag_v2_production`).
- Không xóa cây model ONNX (`models\bge-m3-onnx-fp32`).
- Không xóa file khi chưa liệt kê và xác minh.
- Không đụng ổ D.
- Không đụng session/state của opencode đang chạy vé AUDIT-ENRICH-MOM.

## Báo cáo
Ghi vào `docs/phieu-viec/ket-qua/don-o-c-may-nha.md`: từng bước đã làm,
dung lượng trước/sau mỗi bước, danh sách file đã xóa. Commit lên
`phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
