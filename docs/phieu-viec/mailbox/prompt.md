# Vé P1.3 — Đóng dấu kho thật: backup + chép canary đè production + chạy B1–B5

Ngày viết: 2026-09-28 (Muse). Chế độ tự lái: Muse ra vé → OMP thực hiện độc lập
trên Windows (luật "không vừa đá vừa thổi còi").
Nhánh: `phieu-viec/rag-fix1`. Không đụng `main`. Máy: `h410asrock` (Win 10 Pro).

## Bối cảnh (đã đạt, không làm lại)

- Vé P1 bước 1 (ĐẠT): kho canary `C:\AIOS_habit_index_ve03\library.sqlite` —
  integrity_check=ok, ONNX dense/sparse 107.331/107.331,
  fingerprint `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`
  khớp E1, pending=0. Đây là file NGUỒN.
- Vé P1.2 (ĐẠT, commit `5647df3`): đường dẫn production thật của collection `tri_thuc`:
  `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
  (file cũ 32.452.608 byte, quick_check=ok). Repo root `D:/Sandbox/AIOS_habbit` đã xác nhận.
  Manifest `config\workspace_chat_rag_v2.local.json` activated →
  runtime_root=`..._production`, profile=`bge_m3_hybrid`. App mở bình thường là đọc
  đúng production, KHÔNG cần đổi config.

## Lệnh cấm ghi ổ D — ngoại lệ một lần có giới hạn

- Ổ D (HDD WDC WD2500AAKX) hỏng dần mặt đĩa; lệnh "cấm ghi ổ D vĩnh viễn" của user
  vẫn hiệu lực cho mọi hoạt động index thường xuyên (embed, migration, vacuum,
  benchmark ghi).
- Nhưng kế hoạch P1 (user chốt 22:43 ngày 27/09, SAU lệnh cấm) yêu cầu đóng dấu kho
  canary thành kho production, mà production nằm trên D. Vì vậy vé này cho phép
  NGOẠI LỆ MỘT LẦN: đúng 1 lần copy 1 file (~1,75GB) từ C sang D theo bước 2 dưới.
  Mọi ghi khác lên D trong vé này đều cấm.
- Fail-closed: backup nằm trên ổ C nên dữ liệu an toàn dù D có hỏng giữa chừng.
  Bất kỳ lỗi I/O nào trên D trong vé này → DỪNG NGAY, báo nguyên văn, giữ nguyên
  mọi file, không thử lại lần 2.
- Sau vé này (ghi chú cho P2/P3): production vẫn nằm trên ổ hỏng dần — cần vé di
  chuyển production sang ổ C + cập nhật manifest. Ghi nhận trong báo cáo, không
  làm trong vé này.

## Cách làm (đúng thứ tự)

1. Backup: copy file production trên D →
   `C:\AIOS_backup_production_2026-09-28\library.sqlite.backup` (đọc D, ghi C;
   tạo thư mục C nếu chưa có). `PRAGMA quick_check` trên file backup (mode=ro)
   phải = `ok`. Ghi sha256 + kích thước file D cũ vào báo cáo.
2. Copy: `C:\AIOS_habit_index_ve03\library.sqlite` → chép đè lên đường dẫn
   production trên D. MỘT lần duy nhất. I/O error → DỪNG theo mục trên.
3. Verify: sha256(file đích trên D) == sha256(file nguồn canary trên C); kích
   thước khớp; `PRAGMA quick_check` file đích (mode=ro) = `ok`.
4. Smoke test trên app thật: mở app bình thường (không sửa config — manifest đã
   trỏ production). In đường dẫn library app thật sự mở (one-liner của P1.2) để
   xác nhận đúng file vừa chép. Chạy B1–B5 (B4 LOẠI khỏi chấm điểm theo kế hoạch
   chuỗi E vì ground truth không có trong corpus — không bịa đáp án). Ghi nguyên
   văn kết quả từng câu, thời gian chạy, backend dùng (kỳ vọng default ONNX).
5. Không làm gì thêm: không embed, không vacuum, không đổi manifest/env,
   không sửa code.

## Cấm kỵ

- Ngoại trừ bước 2, cấm mọi ghi lên ổ D.
- Không `git pull` tạo merge — `git fetch` + làm trên nhánh vé. Không đụng `main`.
- Không sửa code/test để "cho qua" — fail thì báo nguyên vẹn kèm số đo.

## Nghiệm thu

Báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md` gồm:
1. sha256 + kích thước: file nguồn canary, file D cũ, file backup trên C,
   file đích trên D (sau chép).
2. quick_check của 3 file (backup, nguồn, đích) — đều phải `ok`.
3. Thời gian copy + có/không I/O error trên D.
4. Đường dẫn library app thật sự mở + kết quả B1–B5 nguyên văn (B4 loại),
   backend, thời gian chạy.
5. Hostname máy chạy, thời điểm kiểm tra, nhánh.

Tiêu chí ĐẠT: backup ok trên C + sha256 đích == nguồn + quick_check đích ok +
app mở đúng kho production mới + B1/B2/B3/B5 đúng nội dung (không bịa),
B1–B5 chạy không lỗi.

## Sau vé này

P1.3 đạt → P1 hoàn tất (kho thật đã đóng dấu) → Muse phát hành Vé P2
(mang sang máy công ty KDTVN-PC0575). Không tự mở P2 trước verdict.
