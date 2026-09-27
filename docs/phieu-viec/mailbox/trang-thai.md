# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: Vé V1 — xác minh F1–F4 (lược đồ `error_cases` + bảng giải thích mã lỗi + sổ chống trùng) trên Windows máy nhà (chỉ chạy kiểm thử; cấm ghi chỉ mục hoặc nhúng dữ liệu)
- Ticket trước: Vé 0.3 — ĐÃ DUYỆT 2026-09-28 ~03:10: migration GPU hoàn tất 99.003/99.003 khối trên index ổ C (`C:\AIOS_habit_index_ve03\library.sqlite`), `pending=0`, ONNX dense/sparse 107.331/107.331, `integrity_check=ok`, không lỗi I/O; báo cáo `docs/phieu-viec/ket-qua/VE0_3_khac-phuc-disk-io-resume.md` (commit `01c3d93`); ghi chú: repo làm việc ban đầu nằm trên D nên có 1 lần ghi metadata Git trên D trước khi phát hiện cấm — index SQLite trên D KHÔNG bị ghi; user đã chốt cấm ghi D vĩnh viễn, D chỉ đọc.
- Ticket trước nữa: Vé 0.2 — ĐÃ DUYỆT 2026-09-27 ~18:42 (chẩn đoán disk I/O, ổ D hỏng dần mặt đĩa)
- Commit: `de11b64767b2f7da949c4b7e16fa0ec0eba4e4b0` (mã tại lần chạy F1/F4)
- Báo cáo: `docs/phieu-viec/ket-qua/VE_V1_verify-F1-F4-windows.md`
- Ghi chú: Muse 2026-09-28 ~03:10 +07 — verdict Vé 0.3 ĐẠT, phát hành Vé V1 theo kế hoạch (verify F1–F4 trước, P1 đóng dấu kho thật sau). Chế độ tự lái: OMP chỉ đọc + chạy test, không sửa code để "cho qua".
- Ghi chú: OMP 2026-09-28 03:16 +0700 — báo cáo Vé 0.3 đã bổ sung kết quả kiểm thử; 3.194 đạt, 4 bỏ qua, 14 thất bại, 10 lỗi do phụ thuộc, manifest và fixture (xem báo cáo). Ticket V1 vẫn ở trạng thái `moi`.
- Ghi chú: OMP 2026-09-28 03:40 +0700 — đã nhận vé, kiểm tra mã `c6aa0839a0f727c7edd6e507d1da423130936e7e`; dùng bản sao riêng trên ổ C để không ghi ổ D; tạo môi trường Python 3.11.14 theo quy tắc kho mã, không sửa mã hoặc ghi chỉ mục.
- Ghi chú: OMP 2026-09-28 03:42 +0700 — bản sao sạch trên C đã lấy mã `c6aa0839a0f727c7edd6e507d1da423130936e7e`; môi trường Python 3.11.14 với `pytest 8.4.2` và `xlrd 2.0.2` đã sẵn sàng. Dùng Python 3.11 theo quy tắc kho mã vì dự án yêu cầu dưới 3.12; chỉ chạy kiểm thử, không chạm dữ liệu hoặc chỉ mục thật.
- Ghi chú: OMP 2026-09-28 03:43 +0700 — `tests/test_rag_v2_ingest_manifest.py` đạt 6/6 trên Windows, Python 3.11.14; chạy tại commit mã `c6aa0839a0f727c7edd6e507d1da423130936e7e`, không ghi chỉ mục thật.
- Ghi chú: OMP 2026-09-28 03:44 +0700 — lần thu thập đầu bộ F1/F4 dừng vì thiếu `openpyxl`; đã cài `openpyxl 3.1.5` vào môi trường tạm trên C và chạy lại.
- Ghi chú: OMP 2026-09-28 03:46 +0700 — bộ kiểm tra F1/F4 chạy tại mã `de11b64767b2f7da949c4b7e16fa0ec0eba4e4b0`: 16 đạt, 10 lỗi thiết lập; F1 đạt 15/15, F4 đạt 1/11 và 10 lỗi vì thiếu bảng tính nguồn ở đường dẫn mặc định. Tiêu chí 26/26 chưa đạt; không sửa mã, dữ liệu hoặc chỉ mục.
- Ghi chú: OMP 2026-09-28 03:48 +0700 — lệnh `git pull` theo yêu cầu người dùng đã chạy trên kho mã D trước khi đọc chỉ dẫn Vé V1, nên Git đã ghi siêu dữ liệu và cập nhật tệp kho mã trên D; không ghi chỉ mục SQLite. Mọi commit tiếp theo được tạo từ bản sao riêng trên C.
- Ghi chú: OMP 2026-09-28 03:52 +0700 — đã hoàn tất báo cáo Vé V1; bộ kiểm tra sổ chống trùng 6/6, F1/F4 16 đạt và 10 lỗi thiết lập do thiếu tệp nguồn. Tiêu chí 26/26 chưa đạt; trạng thái chờ duyệt, không mở Vé P1.
