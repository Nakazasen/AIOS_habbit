# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: OMP hoàn thành dry-run 50/99 nguồn local lúc 2026-09-27 05:36 +0700 — cộng dồn 74.890 chunk/53.648 chunk truy xuất được. Tệp `.xlsm` 64.087 chunk được giữ trong phạm vi; bộ nạp dùng `upsert_chunks` giao dịch sau khi `replace_document_chunks` vượt trần 32.766 tham số SQLite; chạy thử 33.000 chunk đạt. Một `.xls` và một `.ppt` không trích được. Chỉ mục thật chưa đổi.
- Cập nhật lần cuối: 2026-09-27 05:36 +0700 (OMP — dry-run local 50 nguồn)
