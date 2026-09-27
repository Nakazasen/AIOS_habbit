# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ghi chú: OMP 2026-09-28 03:58 +0700 — đã nhận Vé V1.2, checkout `65f45b5` trên bản sao sạch C (`C:/tmp/omp-ve-v1-clean`); không ghi ổ D, chỉ đọc + chạy test.
- Ghi chú: OMP 2026-09-28 04:10 +0700 — đã quét tên chính xác 4 file xls trên `C:/Users`, `D:/`, `C:/tmp` (bỏ `.git`/`.venv`/`Windows`): không thấy file nào; không thấy thư mục `aios_data`/`dieu_tra_loi`; file gần giống nhất (`02XC_自己診断表示一覧表-VN.xls` 1.279.488 byte trên D, `SCT自動調整エラーコード一覧.xls` 35.840 byte) khác tên/kích thước vé nên không dùng. Chạy lại suite: manifest 6/6; F1/F4 16 đạt + 10 lỗi thiết lập (thiếu nguồn). Đang ghi báo cáo.
- Ticket hiện tại: Vé V1.2 — chạy nốt 10 test F4 cần dữ liệu thật trên Windows máy nhà (chỉ chạy kiểm thử; cấm ghi chỉ mục hoặc nhúng dữ liệu)
- Ticket trước: Vé V1 — CHƯA ĐẠT 2026-09-28 ~03:53 (xác minh F1–F4 trên Windows): manifest 6/6 ✓, F1 15/15 ✓, F4 1/11 + 10 error ở fixture setup do thiếu 4 file nguồn xls trên máy Windows (`AIOS_DATA_DIR` chưa đặt, đường dẫn mặc định không tồn tại); 0 test FAILED — không phải lỗi code, báo cáo trung thực. Báo cáo: `docs/phieu-viec/ket-qua/VE_V1_verify-F1-F4-windows.md`. Đã đối chiếu diff độc lập c6aa083...4da41ae: 7 commit chỉ sửa mailbox/báo cáo, không đụng code.
- Ticket trước nữa: Vé 0.3 — ĐÃ DUYỆT 2026-09-28 ~03:10: migration GPU hoàn tất 99.003/99.003 khối trên index ổ C (`C:\AIOS_habit_index_ve03\library.sqlite`), `pending=0`, ONNX dense/sparse 107.331/107.331, `integrity_check=ok`, không lỗi I/O; báo cáo `docs/phieu-viec/ket-qua/VE0_3_khac-phuc-disk-io-resume.md` (commit `01c3d93`).
- Commit: `73855e73dcefad5550ca496900c24635f73c31bd` (push báo cáo Vé V1.2; mã lúc chạy test: `e0b77d400a677ca2ec6d184c55f41d70e390853b`)
- Báo cáo: `docs/phieu-viec/ket-qua/VE_V1_2_F4-voi-du-lieu-windows.md`
- Ghi chú: OMP 2026-09-28 04:15 +0700 — đã xong Vé V1.2 (không tìm thấy 4 file nguồn nên dừng đúng bước 6 của vé): manifest 6/6, F1 15/15, F4 1/11 + 10 lỗi thiết lập; 0 test FAILED; không ghi index, không ghi D. Chờ duyệt, không mở P1.
- Ghi chú: Muse 2026-09-28 ~03:53 +07 — verdict Vé V1 CHƯA ĐẠT (thiếu nguồn dữ liệu, không phải lỗi code); phát hành Vé V1.2 theo chế độ tự lái; đạt V1.2 mới tới P1.
