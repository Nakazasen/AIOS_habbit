# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: OMP kiểm kê hoàn tất 2026-09-27 05:06 +0700 — local 890 file, ZIP 2.147 mục, tổng dung lượng giải nén 936.853.642 byte; chưa file nào có đường dẫn nguồn trùng 74 doc trong index. Dry-run batch ảnh đầu 10/61: 132 chunk/93 retrievable; OCR Tesseract hiện chỉ chọn `eng`. Không ghi index.
- Cập nhật lần cuối: 2026-09-27 05:06 +0700 (OMP — kiểm kê đầy đủ, dry-run lô ảnh đầu)
