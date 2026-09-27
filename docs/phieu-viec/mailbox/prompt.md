# Vé 0.3 — Xử lý nguyên nhân disk I/O + resume migration GPU (cấm ghi ổ D hiện tại)

Ngày viết: 2026-09-27 (Muse). Branch: `phieu-viec/rag-fix1`. Không đụng `main`.

## Bối cảnh

- Vé 0.2 (ĐÃ DUYỆT 2026-09-27): nghi phạm số 1 = mặt đĩa ổ D hỏng dần (`WDC WD2500AAKX-083CA1`: 513 cung tái cấp phát + 9 lần tái cấp phát + 1 cung chờ xử lý — số từ bộ nhớ đệm CrystalDiskInfo tháng 12/2025, CHƯA có số tươi). Đã loại đĩa đầy / quyền / Defender / log hệ thống bằng số. Lỗi I/O rời rạc, test ghi 1MB OK. Lệnh cấm ghi vẫn giữ.
- Mẻ migration GPU dừng ở 6.128/99.003 (6,19%); index 1.750.740.992 byte đóng băng từ 16:48:22, nguyên vẹn.
- Báo cáo: `docs/phieu-viec/ket-qua/VE0_2_chan-doan-disk-io-error.md`

## Cấm kỵ

- CẤM ghi bất cứ thứ gì lên ổ D (HDD chứa index cũ) cho đến khi bước 2 xác nhận ổ mới an toàn. Mọi test ghi chỉ làm trên ổ đích.
- Không `git pull` (Vé 0 đã có lần merge `839ceea` dù prompt cấm — lần này không lặp lại).
- Không đụng `main`; mọi commit riêng trên `phieu-viec/rag-fix1`.
- Luật vòng tròn: migration GPU là việc OMP giữ index làm trên máy nhà — đúng vai OMP.

## Cách làm (theo đúng thứ tự)

### Bước 1 — Xác nhận số tươi về ổ D (chỉ đọc, chưa ghi gì)

1. SMART tươi: mở CrystalDiskInfo chụp màn hình tab ổ `WDC WD2500AAKX-083CA1`, hoặc cài `smartctl -a` (gsmartcontrol) cho Disk 0. Ghi số: 05 (Reallocated Sector Count), C4 (Reallocation Event Count), C5 (Current Pending Sector), C6 (Uncorrectable Sector Count), C7 (UDMA CRC Error Count), % health.
2. `chkdsk D: /scan` ở PowerShell quyền nâng cao (quét trực tuyến, không cần khởi động lại). Ghi kết quả: có lỗi hệ tệp không.
3. Nếu SMART tươi xấu hơn hẳn (Reallocated tăng so với 513, hoặc C6 > 0) → ghi rõ trong báo cáo, vẫn làm bước 2 ngay (không cần hỏi).

### Bước 2 — Đổi nơi đặt index sang ổ khỏe

1. Chọn ổ đích: SSD 120GB (ổ C) hoặc ổ khác có sẵn trên máy. Lưu ý: ổ C còn ~5,85 GiB; file index 1,75 GiB + bản backup 1,75 GiB = ~3,5 GiB. Tính dung lượng trước khi chọn; nếu không đủ, đề xuất phương án (dọn chỗ / ổ khác) và ghi rõ trong báo cáo — KHÔNG tự quyết mua/tháo ổ cứng.
2. Copy `library.sqlite` sang ổ đích (robocopy có kiểm tra, hoặc copy rồi so sánh kích thước + sha256 hai bản).
3. Trên bản sao ở ổ mới: mở bằng sqlite3, chạy `PRAGMA integrity_check;` → phải đạt `ok`.
4. Chỉ sau khi integrity_check đạt ở ổ mới: đổi đường dẫn index trong script migration sang ổ mới. Bản trên ổ D giữ nguyên làm sao lưu lạnh (không xóa).

### Bước 3 — Backup mới + resume migration (dry-run/mẫu nhỏ trước)

1. Trước resume: tạo backup tươi của index trên ổ mới (file sibling), kiểm tra integrity của backup đạt `ok` — fail-closed nếu không ok.
2. Resume migration từ checkpoint với `batch_size = 16` (theo đề xuất Vé 0; không để 2 như cũ).
3. Chạy mẫu trước: 5 batch đầu, đo timing từng batch + xác nhận không lỗi I/O. Nếu mẫu sạch → resume toàn bộ 92.875 khối còn lại. Ghi nhịp mới + ETA mới.
4. Nếu `disk I/O error` tái diễn trên ổ mới → DỪNG mẻ ngay, giữ nguyên trạng, báo cáo (vé sau điều tra tiếp — không tự retry mù).

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE0_3_khac-phuc-disk-io-resume.md` gồm:

1. Số SMART tươi (05/C4/C5/C6/C7) + kết quả `chkdsk D: /scan`.
2. Ổ đích đã chọn + dung lượng còn lại; kết quả `integrity_check` trên ổ mới (`ok`); đường dẫn index mới.
3. Backup tươi (đường dẫn + integrity `ok`).
4. Kết quả mẫu 5 batch (timing, không lỗi) → quyết định resume toàn bộ / dừng; nhịp mới + ETA mới; số khối đã migrate / tổng.

Số liệu từ lần đo thật trên máy h410asrock, ghi hostname + thời gian đo.
