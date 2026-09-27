# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Vé V1 — Verify F1–F4 (schema error_cases + glossary + sổ chống trùng) trên Windows máy nhà (chỉ chạy test, cấm ghi index/embed)
- Ticket trước: Vé 0.3 — ĐÃ DUYỆT 2026-09-28 ~03:10: migration GPU hoàn tất 99.003/99.003 khối trên index ổ C (`C:\AIOS_habit_index_ve03\library.sqlite`), `pending=0`, ONNX dense/sparse 107.331/107.331, `integrity_check=ok`, không lỗi I/O; báo cáo `docs/phieu-viec/ket-qua/VE0_3_khac-phuc-disk-io-resume.md` (commit `9f243ec`); ghi chú: repo làm việc ban đầu nằm trên D nên có 1 lần ghi metadata Git trên D trước khi phát hiện cấm — index SQLite trên D KHÔNG bị ghi; user đã chốt cấm ghi D vĩnh viễn, D chỉ đọc.
- Ticket trước nữa: Vé 0.2 — ĐÃ DUYỆT 2026-09-27 ~18:42 (chẩn đoán disk I/O, ổ D hỏng dần mặt đĩa)
- Commit mới nhất: `9f243ec` (báo cáo Vé 0.3)
- Báo cáo: (OMP ghi khi Vé V1 xong)
- Ghi chú: Muse 2026-09-28 ~03:10 +07 — verdict Vé 0.3 ĐẠT, phát hành Vé V1 theo kế hoạch (verify F1–F4 trước, P1 đóng dấu kho thật sau). Chế độ tự lái: OMP chỉ đọc + chạy test, không sửa code để "cho qua".
