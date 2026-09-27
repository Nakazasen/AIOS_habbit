# Vé 0.3 — Chuyển index sang ổ C (SSD) + resume migration GPU (CẤM ghi ổ D vĩnh viễn)

Ngày viết: 2026-09-27 (Muse). Sửa lần 2 lúc 19:04 theo QUYẾT ĐỊNH CỦA USER (bỏ phương án ổ mới).
Sửa lần 3 lúc 20:11 theo QUYẾT ĐỊNH CỦA USER: mẫu sạch → resume ngay tối nay, không đo thêm; báo ETA ngay khi resume chạy.
Sửa lần 4 lúc 20:54 theo QUYẾT ĐỊNH CỦA USER: mẻ ghi ngoài tối đa 50–100 khối/chốt (batch GPU trong giữ 2); mẫu = 1 mẻ to, sạch thì resume toàn bộ 92.875, khỏi đo 3 mốc; sập thì chạy lại cả mẻ (trừ I/O error thì dừng).
Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- Vé 0.2 (ĐÃ DUYỆT): ổ D (HDD WDC WD2500AAKX) hỏng dần mặt đĩa. Số SMART tươi (Bước 1 đã xong, xem trang-thai.md 18:38): 05 Reallocated 769 (tăng từ 513), C4 Event 10 (tăng từ 9), C5 Pending 0, C6 0, C7 UDMA CRC 200 (chuẩn), Health "Chú ý" (vàng), 38°C; SSD ổ C tốt 91% life.
- Mẻ migration GPU dừng ở 6.128/99.003 (6,19%); index 1.750.740.992 byte đóng băng từ 16:48:22, nguyên vẹn.
- Báo cáo Vé 0.2: `docs/phieu-viec/ket-qua/VE0_2_chan-doan-disk-io-error.md`

## Cấm kỵ (user chốt 19:04)

- CẤM VĨNH VIỄN ghi bất cứ byte nào lên ổ D. Ổ D từ nay CHỈ ĐỌC để cứu dữ liệu cũ khi cần — không ghi, không sửa, không chkdsk /f.
- Không `git pull` (Vé 0 đã có lần merge `839ceea` dù prompt cấm — không lặp lại).
- Không đụng `main`; mọi commit riêng trên `phieu-viec/rag-fix1`.

## Cách làm (theo đúng thứ tự)

### Bước 1 — ĐÃ XONG
SMART tươi đã có (trang-thai.md, OMP 18:38). `chkdsk D: /scan` BỎ QUA theo quyết định user (ổ D chuyển sang chỉ đọc, không cần quét nữa).

### Bước 2 — Chuyển index sang ổ C (SSD)

1. Kiểm tra dung lượng trống ổ C (hiện ~5,8GB). Cần: index 1,75GB + backup tươi 1,75GB ≈ 3,5GB. Nếu thiếu → DỌN CHỖ TRƯỚC (xóa file tạm, cache, thùng rác; KHÔNG xóa dữ liệu dự án/code/index), ghi rõ đã dọn gì và dung lượng trước/sau.
2. Copy `library.sqlite` từ D sang C (robocopy có verify, hoặc copy rồi so kích thước + sha256 hai bản — phải khớp 100%).
3. Trên BẢN SAO Ở Ổ C: mở bằng sqlite3, chạy `PRAGMA integrity_check;` → phải đạt `ok`. CHƯA ok thì DỪNG NGAY, báo cáo — không làm tiếp bước nào.
4. Chỉ sau khi integrity_check đạt ở ổ C: đổi đường dẫn index trong script migration sang ổ C. Bản trên ổ D giữ nguyên làm sao lưu lạnh (không xóa, không ghi).

### Bước 3 — Backup mới + thử mẫu trên ổ C

1. Backup tươi của index TRÊN Ổ C (file sibling), `integrity_check` của backup phải `ok` — fail-closed nếu không ok.
2. Cấu hình batch (user chốt 20:54): mẻ ghi NGOÀI TỐI ĐA 50–100 khối mỗi chốt (đề xuất 100), batch GPU TRONG giữ nguyên 2 (không đổi).
3. Chạy MẪU = 1 MẺ TO trên ổ C (50–100 khối): đo nhịp mẻ + `integrity_check` sau mẻ + theo dõi I/O error trong log. Không cần đo 3 mốc.
4. Mẫu SẠCH (integrity ok, nhịp ổn, không I/O error) → RESUME NGAY TRONG TỐI NAY toàn bộ 92.875 khối còn lại (99.003 − 6.128), không đo thêm gì nữa. Báo ETA mới NGAY KHI resume bắt đầu chạy (ghi vào báo cáo + cập nhật trang-thai.md).
5. Mẻ sập giữa chừng (process chết, mất điện...) → CHẠY LẠI CẢ MẺ từ checkpoint — user chấp nhận rủi ro này (ổ C khỏe, backup mới đã có). Chỉ DỪNG NGAY + báo cáo khi sập do disk I/O error.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE0_3_khac-phuc-disk-io-resume.md` gồm:

1. Dung lượng ổ C trước/sau dọn (nếu có dọn, liệt kê đã dọn gì).
2. Kích thước + sha256 hai bản copy (D và C) — phải khớp; `integrity_check` trên ổ C (`ok`); đường dẫn index mới.
3. Backup tươi (đường dẫn + integrity `ok`).
4. Kết quả mẫu: nhịp mẻ to, integrity sau mẫu, có/không I/O error → quyết định resume toàn bộ / dừng (ghi rõ lý do nếu dừng hoặc phải chạy lại).
5. Nếu resume: nhịp ổn định + ETA cập nhật; số khối đã migrate / tổng (6.128 + số mới / 99.003).

Số liệu từ lần đo thật trên máy h410asrock, ghi hostname + thời gian đo.
