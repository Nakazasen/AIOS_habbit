# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: OMP kiểm kê xong 2026-09-27 03:10 +0700 — local 890 file (783 csv, 61 png, 17 xlsx, 12 xlsm, 6 pptx, 3 msg, 1 ppt, 1 xls, 1 zip 818MB) + zip 2147 file (1175 gz, 423 log, 232 xlsx, 101 txt, 88 pdf...). Baseline index: 74 doc/1272 chunk/1064 retrievable, pending 0, integrity ok. Đang dry-run extractor.
- Cập nhật lần cuối: 2026-09-27 03:00 +0700 (OMP — nhận ticket G1)
