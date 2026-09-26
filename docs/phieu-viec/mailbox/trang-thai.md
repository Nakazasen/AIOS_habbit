# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: OMP hoàn thành dry-run 99/99 nguồn local (81.503 chunk/58.543 truy xuất được) và 14/334 nguồn ZIP (4.925/3.770) lúc 2026-09-27 05:54 +0700. Ba `.xls` đầu ZIP lỗi do thiếu `xlrd`; PDF 157,3 MiB đã xử lý riêng, không lỗi. Chỉ mục thật chưa đổi.
- Cập nhật lần cuối: 2026-09-27 05:54 +0700 (OMP — ZIP 14/334)
