# Vé 0.2 — Chẩn đoán lỗi `sqlite3.OperationalError: disk I/O error` (KHẨN, CHỈ ĐỌC, không sửa)

Ngày viết: 2026-09-27 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- Vé 0 (ĐÃ DUYỆT): nhịp rơi 4,2× do chi phí SQLite lặp lại ở mỗi batch 2 (2 kết nối/batch: kiểm tra từng hàng rồi ghi dense+sparse trong 1 giao dịch, đồng hồ batch không tính overhead). Batch cuối chết ở `_upsert_batch` với `sqlite3.OperationalError: disk I/O error` lúc 16:48:24; mẻ đã dừng (6.128/99.003 = 6,19%).
- **Chưa được giải thích:** nguyên nhân của `disk I/O error`. CẤM cho ghi tiếp (kể cả chạy mẫu) cho đến khi nguyên nhân rõ. Vé này CHỈ CHẨN ĐOÁN, không sửa. Sửa là vé khác.
- Ghi nhận: Vé 0 có một lần `git pull` tạo merge `839ceea` dù prompt cấm — đã nhắc, lần này KHÔNG lặp lại.

## Cách làm — CHỈ ĐỌC, CẤM TUYỆT ĐỐI ghi DB

Cấm: ghi `library.sqlite` (kể cả qua script migration), vacuum, restart/pause bất cứ tiến trình nào, `git pull`, sửa code, đụng backup.

Điều tra theo đúng thứ tự:

1. **System log quanh 16:48:24**: Event Viewer → Windows Logs → System, lọc lỗi/warning từ nguồn `disk`, `Ntfs`, `nvstor`/`storahci`/`iaStorAC` trong khung 16:40–17:00. Ghi mã sự kiện + nội dung.
2. **Sức khỏe ổ đĩa**: SMART (CrystalDiskInfo chụp số liệu hoặc `smartctl -a`), đặc biệt Reallocated Sector Count / Pending Sector / UDMA CRC Error Count. Ghi model ổ + % health.
3. **Filesystem/thư mục index**: dung lượng trống còn lại; thư mục chứa `library.sqlite` có còn file `-wal`/`-shm`/`-journal` tồn đọng không (tên + kích thước + mtime).
4. **SQLite chỉ-đọc** (mở kết nối `mode=ro` hoặc `PRAGMA query_only=ON`): `PRAGMA page_count;`, `PRAGMA freelist_count;`, `PRAGMA page_size;`, `PRAGMA journal_mode;`, `SELECT COUNT(*)` trên bảng vector dense ONNX. Không chạy `integrity_check` lại (Vé 0 đã làm, kết quả `ok`).
5. **Test ghi kiểm soát**: tạo 1 file test tạm ~1MB trong cùng thư mục chứa index (không phải file DB), ghi/xóa ngay, đo có lỗi không. Đây là file test tạm duy nhất được phép tạo; xóa ngay sau khi đo.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE0_2_chan-doan-disk-io-error.md` gồm:

1. Chỉ mặt nguyên nhân `disk I/O error` (phần cứng / filesystem / quyền / phần mềm chặn ghi như AV — kèm số liệu và log trích dẫn).
2. Đề xuất khắc phục cho vé sau (vé này KHÔNG sửa; nếu nguyên nhân phần cứng thì nêu phương án đổi nơi đặt index).
3. Cập nhật nhịp/ETA hiện tại (mẻ vẫn dừng).

Số liệu từ lần đo thật trên máy h410asrock, ghi hostname + thời gian đo.
