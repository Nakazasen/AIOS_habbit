# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: chuỗi E đã xong cả 4 phiếu (E1 điều tra, E2 synthesis, E3 dọn XML, E4 default ONNX). Tiếp theo: G1 ingest dữ liệu LSU + case lỗi, rồi G2 kiểm thử 10 câu, rồi F1–F5 Bước 0 (hạn 28–30/09).
- Cập nhật lần cuối: 2026-09-27 ~02:58 +0700 (Muse — phát hành ticket G1)
