# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: G1 — kiểm kê + ingest dữ liệu LSU và case lỗi theo quy trình D2 (sau E3/E4); báo rõ loại file extractor không hỗ trợ.
- Ticket trước: E4 — ĐẠT (Muse review 2026-09-27: diff 77c804b6+3aa4280 khớp báo cáo; alias onnx/auto→onnx, onnx_int8 tách riêng dir/checksum/fingerprint; fail-closed khi thiếu model; 63 test liên quan đạt; full suite 3.146 passed + 23 lỗi môi trường cũ, không PASS giả; index chỉ đọc pending 0, integrity ok)
- Mã nguồn E4: `77c804b6b26dd433f18be39e0770d06e0b559931` (+ sửa worker `3aa4280fe1e968da635e86ba7b28dff760c6dc40`)
- Báo cáo E4: `docs/phieu-viec/ket-qua/FIX3_backend-E4-default-onnx.md`
- Ghi chú: OMP đã đối chiếu nguồn với chỉ mục 2026-09-27 05:03 +0700 — 890/890 tệp local và 2.147/2.147 mục trong ZIP chưa có đường dẫn trong 74 tài liệu chỉ mục. Chính sách tách 783 CSV/log khỏi thư viện chữ; ZIP loại log/txt thô, tệp lồng/định dạng lạ. Dry-run toàn bộ cũ timeout 60 phút, chỉ đọc. Runner đã chia lô có checkpoint; 5/10 tệp local đầu đã xử lý, chưa ghi chỉ mục.
- Cập nhật lần cuối: 2026-09-27 05:03 +0700 (OMP — đối chiếu nguồn và chia lô dry-run)
