# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: OMP dry-run thử 10 file xong 2026-09-27 03:55 +0700 — 8822 chunk/8083 retrievable; 3 file xls lỗi thiếu bộ đọc xlrd; 1 xlsx cho 6506 chunk (cảnh báo file lớn). Pipeline dùng chunk 1200 (đã khớp runner). Đang chạy dry-run toàn bộ local 40 file.
- Cập nhật lần cuối: 2026-09-27 03:00 +0700 (OMP — nhận ticket G1)
