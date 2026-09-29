# Ticket XẾP HÀNG: Dọn ổ C máy nhà (user đã cho phép 2026-09-29 ~20:10 +07)

## Bối cảnh
Ổ C còn ~2.5GB trống, AIOS chiếm ~21GB. User cho phép dọn, mục tiêu lấy lại ~8GB.
Thứ tự từ an toàn nhất đến rủi ro nhất. Mỗi bước: liệt kê → xác minh → xóa → báo cáo
dung lượng thu hồi.

## Các bước (làm theo đúng thứ tự, dừng ngay nếu bước nào không chắc chắn)

### Bước 1: Rác tmp (an toàn nhất)
- Quét `C:\Windows\Temp`, `%TEMP%`, `local_runs\**\tmp`, `scratch\` các file
  quá 7 ngày không đụng tới.
- Chỉ xóa file tmp/log/cache. KHÔNG xóa file đang mở/lock.
- Báo cáo: dung lượng thu hồi.

### Bước 2: venv trùng lặp
- Liệt kê tất cả venv (`venv`, `.venv`, `env*`) trong `D:\Sandbox\AIOS_habbit` và ổ C.
- Giữ lại 1 venv đang dùng (kiểm tra `sys.prefix` của OMP hiện tại).
- Xóa các venv trùng không dùng tới. Trước khi xóa: xác nhận không có package
  đặc biệt chỉ cài ở venv đó (so `pip freeze`).
- Báo cáo: danh sách xóa + giữ + dung lượng thu hồi.

### Bước 3: Worktree vé 0.3
- Vé 0.3 đã đóng. Kiểm tra worktree còn tồn tại không.
- Nếu còn: xác nhận mọi commit đã push/merge, rồi `git worktree remove`.
- Báo cáo: dung lượng thu hồi.

### Bước 4: 2 backup cũ (CẦN XÁC MINH TRƯỚC KHI XÓA)
- Liệt kê các backup index trên ổ C (VD: `C:\AIOS_habit_index_*`).
- Với mỗi backup định xóa: chạy `PRAGMA integrity_check` trên bản GIỮ LẠI,
  phải trả về `ok` mới được xóa bản cũ.
- KHÔNG xóa nếu chỉ còn 1 bản backup duy nhất của index production.
- Báo cáo: từng file xóa (đường dẫn + SHA trước khi xóa) + kết quả integrity_check
  của bản giữ lại.

### Bước 5: tri_thuc — CHƯA LÀM (chờ E2v3 đóng hẳn)
- Ghi chú rõ: bỏ qua bước này trong vé hiện tại.

## Cấm tuyệt đối
- Không xóa index production đang dùng (`workspace_chat_rag_v2_production`).
- Không xóa cây model ONNX (`models\bge-m3-onnx-fp32`).
- Không xóa file khi chưa liệt kê và xác minh.
- Không đụng ổ D.

## Báo cáo
Ghi vào `docs/phieu-viec/ket-qua/don-o-c-may-nha.md`: từng bước đã làm,
dung lượng trước/sau mỗi bước, danh sách file đã xóa. Commit lên
`phieu-viec/rag-fix1`, `trang-thai.md` → `xong-cho-duyet`.
