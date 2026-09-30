# Ticket XẾP HÀNG: don-canary — dọn kho canary 2,4GB trên ổ C

## Bối cảnh
`C:\AIOS_habit_index_ve03\library.sqlite` (2,4GB) là kho canary từ Vé 0.3.
Production `C:\AIOS_p1_4\tri_thuc\library.sqlite` chạy ổn định từ P1.3/P1.4
(SHA ghim `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`).
User đã duyệt dọn sau khi xác minh bản giữ lại an toàn.

## Việc cần làm
1. Băm SHA-256 `C:\AIOS_p1_4\tri_thuc\library.sqlite`, đối chiếu khớp ghim trên;
   chạy `PRAGMA integrity_check` → phải `ok`.
2. Chỉ khi cả hai đạt: xóa toàn bộ `C:\AIOS_habit_index_ve03\`
   (`library.sqlite` + file script/cache migration `_run_ve03_*`,
   `model-verify-cache`, `resume`, `sample`).
3. Ghi SHA đã đối chiếu + dung lượng thu hồi vào báo cáo.

## Cấm
- Chỉ xóa trong `C:\AIOS_habit_index_ve03\`. Tuyệt đối không đụng production,
  không đụng backup `C:\AIOS_backup_production_2026-09-28\`, không đụng ổ D.
- Không merge `main`. Không force-push.

## Báo cáo
`docs/phieu-viec/ket-qua/don-canary.md`. Commit lên `phieu-viec/rag-fix1`,
`trang-thai.md` → `xong-cho-duyet`.
