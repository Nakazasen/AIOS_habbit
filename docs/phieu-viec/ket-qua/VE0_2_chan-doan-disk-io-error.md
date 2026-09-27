# Báo cáo Vé 0.2 — Chẩn đoán lỗi `sqlite3.OperationalError: disk I/O error`

Máy đo: `h410asrock`. Thời gian đo: 2026-09-27 18:13–18:35 +07. Chế độ: chỉ đọc, không ghi DB (đúng vé).

## 0. Kết luận trước

Nghi phạm số 1: **mặt đĩa ổ D đã hỏng dần** — ổ HDD `WDC WD2500AAKX-083CA1` (chính là ổ chứa `library.sqlite`) có 513 cung đã tái cấp phát + 9 lần tái cấp phát + 1 cung đang chờ xử lý theo bộ nhớ đệm CrystalDiskInfo. Lỗi I/O rời rạc đúng lúc mở kết nối ghi khớp kiểu ghi chạm cung lỗi. Đã loại bằng số: đĩa đầy, quyền ghi, Windows Defender chặn, nhật ký hệ thống ghi nhận lỗi đĩa. Số SMART là bộ nhớ đệm cũ (tháng 12/2025) nên vé sau phải đọc lại số tươi trước mọi lần ghi tiếp. Lệnh cấm ghi giữ nguyên.

## 1. Số liệu đo thật (theo đúng thứ tự vé)

### 1.1. Nhật ký hệ thống quanh 16:48:24

- Khung 16:40–17:00, mức lỗi/cảnh báo: chỉ 1 cảnh báo `DCOM 10016` lúc 16:56:37 (quyền kích hoạt COM, không liên quan đĩa) + 2 dòng tin `Win32k 267` lúc 16:48:25/16:48:27 (kiểm tra cảm ứng, không liên quan).
- Quét 7 ngày (20/09–27/09): **0 lỗi** từ `disk`/`Ntfs`/`storahci`/`storport`/`volsnap`, **0 cảnh báo** cùng nhóm.
- Nhật ký ứng dụng 16:40–17:00: chỉ 1 cảnh báo `Dwminit` lúc 16:48:27 (3 giây sau lần ghi cuối, sự kiện màn hình, không phải lỗi đĩa). Các lỗi `.NET Runtime`/`Application Error` trong 7 ngày đều cũ, không trúng thời điểm lỗi.
- Nhật ký `Microsoft-Windows-Windows Defender/Operational` ngày 27/09: **0 sự kiện** mức lỗi/cảnh báo — không có bằng chứng trình diệt virus chặn ghi.

### 1.2. Sức khỏe ổ đĩa (SMART)

- Ổ vật lý: Disk 0 = `WDC WD2500AAKX-083CA1` 250 GB (chính là ổ D chứa index), Disk 1 = `SATA SSD` 120 GB (ổ C). `Get-PhysicalDisk` báo cả hai `Healthy`/`OK` (trạng thái thô của Windows, không thấy lỗi cung).
- Bộ nhớ đệm CrystalDiskInfo (`C:\Program Files\CrystalDiskInfo\Smart`, ngày ghi 2025/12/06 — số cũ, đọc để định hướng, vé sau phải đọc tươi):
  - `WDC WD2500AAKX-083CA1`: trạng thái chú ý (vàng), `ReallocatedSectorsCount` thô **513**, `ReallocationEventCount` thô **9**, `CurrentPendingSectorCount` thô **1**, `UncorrectableSectorCount` thô 0, `C7 UDMA CRC` chuẩn hóa 200 (cáp/bộ điều khiển tốt), giờ chạy 4.999, số lần bật 4.202, 31 °C.
  - `SATA SSD` (ổ C): trạng thái tốt (xanh), tuổi thọ còn 95 %, đã ghi máy chủ 10.931, 4.969 giờ, 33 °C.
- Không lấy được số SMART tươi: `smartctl` chưa cài, `Get-StorageReliabilityCounter` và WMI `root\wmi` đều từ chối quyền (chạy quyền thường), `DiskInfo64.exe` là chương trình giao diện không có dòng lệnh.

### 1.3. Hệ tệp và thư mục index

- Index: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`, kích thước **1.750.740.992 byte**, sửa lần cuối 16:48:22 (đóng băng, khớp Vé 0).
- Không còn file `-wal`/`-shm`/`-journal` cạnh index. File `.aios-library-writer.lock` 1 byte, ngày 08/09 (cũ, không phải khóa đang giữ).
- Ổ D (NTFS): tổng 250.057.060.352 byte, còn trống **7.997.992.960 byte (~7,45 GiB, 3,2 %)**, trạng thái `Healthy`/`OK`. Ổ C còn trống ~5,85 GiB.
- Quyền: `Authenticated Users` có quyền sửa trên cả file và thư mục (đủ quyền ghi). `fsutil`/`chkdsk` cần quyền nâng cao nên chưa chạy được trong vé này.

### 1.4. SQLite chỉ đọc (kết nối `mode=ro` + `PRAGMA query_only=ON`, không chạy `integrity_check`)

- `page_size` 4.096, `page_count` 427.427 (427.427 × 4.096 = đúng kích thước file), `freelist_count` 0, `journal_mode` delete, `locking_mode` normal. Mở chỉ đọc thành công.
- `chunks` tổng 133.144, truy xuất được 107.331. `chunk_embeddings` tổng 14.796, trong đó ONNX `016c…` 14.456 (= 8.328 cũ + 6.128 vừa migrate, khớp Vé 0), PyTorch `ce7f…` 340.
- Nhật ký `local_runs/_g1_gpu_apply.log` (243.449 byte, sửa cuối 16:48:24): dòng cuối là `batch 3064: migrated 2 chunks in 1.7s (total 6128/99003…)`, trong log **không có traceback** — lỗi chỉ hiện ở cửa sổ lệnh, khớp mô tả Vé 0 (chết lúc mở kết nối ghi trong `_upsert_batch`).

### 1.5. Thử ghi có kiểm soát (file tạm duy nhất, đã xóa)

Tạo file `ve02_write_test.tmp` 1 MiB trong cùng thư mục chứa index rồi xóa ngay: ghi **34,9 ms**, tổng cả xóa 35,7 ms, thư mục sạch sau thử. Đường ghi hiện tại vẫn đi được — lỗi lúc 16:48:24 là rời rạc, không phải mất khả năng ghi hoàn toàn.

## 2. Chỉ mặt nguyên nhân và loại trừ

| Giả thuyết | Kết luận | Bằng chứng |
|---|---|---|
| Mặt đĩa ổ D hỏng dần | **Nghi phạm số 1** | Ổ D chính là HDD cũ `WD2500AAKX` với 513 cung tái cấp phát + 9 lần tái cấp phát + 1 cung chờ xử lý; lỗi xảy ra đúng lần I/O đầu tiên khi mở kết nối ghi; firmware đĩa tự che lỗi nên nhật ký hệ thống sạch là bình thường |
| Đĩa đầy | Loại | D còn 7,45 GiB, C còn 5,85 GiB; tiến trình đã ghi52 MB trong mẻ mà không báo đầy |
| Quyền ghi | Loại | `Authenticated Users` có quyền sửa; 3.064 batch trước đó ghi thành công |
| Trình diệt virus chặn | Loại (tạm) | Nhật ký Defender ngày 27/09 không có sự kiện; `productState 393472`. Chưa đọc được `Get-MpComputerStatus` (lỗi `0x800106ba`), vé sau có thể kiểm tra lại |
| Lỗi hệ tệp/nhật ký SQLite | Không có dấu hiệu | Không còn `-wal`/`-shm`/`-journal`, `page_count × page_size` khớp file, `freelist` 0, file đóng sạch — crash xảy ra trước khi ghi nên không làm bẩn file |

Điểm yếu của kết luận: số SMART lấy từ bộ nhớ đệm tháng 12/2025 (cũ ~10 tháng), số hiện tại có thể tệ hơn. Chưa chạy `chkdsk` (cần quyền nâng cao). Vì vậy đây là chẩn đoán mức tin cậy cao nhưng chưa phải bằng chứng tươi — vé sau phải xác nhận lại.

## 3. Đề xuất cho vé sau (vé này không sửa)

1. Giữ lệnh cấm ghi trên ổ D hiện tại.
2. Đọc SMART tươi: mở CrystalDiskInfo chụp màn hình hoặc cài `smartctl -a` cho Disk 0; ghi số `05`/`C4`/`C5`/`C6`/`C7` hiện tại.
3. Chạy `chkdsk D: /scan` ở quyền nâng cao (quét trực tuyến, không cần khởi động lại) trong cửa sổ bảo trì.
4. Đổi nơi đặt index: chuyển `library.sqlite` và bản sao lưu sang ổ khỏe (SSD còn trống nhiều), giữ bản trên HDD làm sao lưu lạnh sau khi `integrity_check` đạt. Ổ C hiện chỉ còn ~5,85 GiB nên không phải chỗ đặt lâu dài cho file 1,75 GiB + bản sao lưu.
5. Sau khi chuyển chỗ: sao lưu tươi + `integrity_check` đạt rồi mới chạy mẫu nhỏ với mẻ ghi ngoài 10–20 (đề xuất Vé 0). Có thể cân nhắc `journal_mode=WAL` sau khi sang ổ khỏe để bớt chu kỳ tạo/xóa journal — đây là giảm hao mòn, không phải chữa phần cứng.

## 4. Nhịp và ETA hiện tại

Mẻ vẫn dừng: kích thước và giờ sửa của index và log đóng băng ở 16:48:22/16:48:24. Đã ghi 6.128/99.003 (6,19 %), còn 92.875 khối. Ngoại suy theo nhịp cuối 0,723 khối/giây: khoảng **128.420 giây (~35,7 giờ)** có điều kiện, chỉ có ý nghĩa sau khi xử lý xong lỗi I/O và chuyển chỗ index.
