# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: OMP hoàn thành dry-run lô local 1 ngày 2026-09-27 05:14 +0700 — 10 ảnh/132 chunk/93 retrievable; có 10 gói tạm cục bộ để dùng lại, lệnh apply dry-run xác nhận sẽ ghi 0 thay đổi. Chỉ mục chưa đổi. Tiếp tục lô local kế.
- Cập nhật lần cuối: 2026-09-27 05:14 +0700 (OMP — dry-run lô local 1)
