# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: Nạp đến checkpoint 3/5 (`next_start=300`): 293 nguồn mới, 1 nguồn trùng toàn bộ; chỉ mục 367 tài liệu / 82.355 `chunk` / 60.702 truy xuất được, ONNX pending `59.638`, `integrity_check=ok`. Bản sao lô 3 `library.sqlite.bak-20260927-074835-812794` đạt `ok`.
- Cập nhật lần cuối: 2026-09-27 07:58 +0700 (OMP — lô nạp 3/5)
