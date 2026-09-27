# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ghi chú: OMP 2026-09-28 03:58 +0700 — đã nhận Vé V1.2, checkout `65f45b5` trên bản sao sạch C (`C:/tmp/omp-ve-v1-clean`); không ghi ổ D, chỉ đọc + chạy test.
- Ticket hiện tại: Vé V1.2 — chạy nốt 10 test F4 cần dữ liệu thật trên Windows máy nhà (chỉ chạy kiểm thử; cấm ghi chỉ mục hoặc nhúng dữ liệu)
- Ticket trước: Vé V1 — CHƯA ĐẠT 2026-09-28 ~03:53 (xác minh F1–F4 trên Windows): manifest 6/6 ✓, F1 15/15 ✓, F4 1/11 + 10 error ở fixture setup do thiếu 4 file nguồn xls trên máy Windows (`AIOS_DATA_DIR` chưa đặt, đường dẫn mặc định không tồn tại); 0 test FAILED — không phải lỗi code, báo cáo trung thực. Báo cáo: `docs/phieu-viec/ket-qua/VE_V1_verify-F1-F4-windows.md`. Đã đối chiếu diff độc lập c6aa083...4da41ae: 7 commit chỉ sửa mailbox/báo cáo, không đụng code.
- Ticket trước nữa: Vé 0.3 — ĐÃ DUYỆT 2026-09-28 ~03:10: migration GPU hoàn tất 99.003/99.003 khối trên index ổ C (`C:\AIOS_habit_index_ve03\library.sqlite`), `pending=0`, ONNX dense/sparse 107.331/107.331, `integrity_check=ok`, không lỗi I/O; báo cáo `docs/phieu-viec/ket-qua/VE0_3_khac-phuc-disk-io-resume.md` (commit `01c3d93`).
- Ghi chú: Muse 2026-09-28 ~03:53 +07 — verdict Vé V1 CHƯA ĐẠT (thiếu nguồn dữ liệu, không phải lỗi code); phát hành Vé V1.2 theo chế độ tự lái; đạt V1.2 mới tới P1.
