# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong`
Ticket hiện tại: dieutra-banner-0494
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `329524c`
`bao_cao`: `docs/phieu-viec/ket-qua/dieutra-banner-0494.md`
`verdict`: **ĐẠT** (Muse review độc lập 2026-09-30 ~12:31 +07: vé chỉ điều tra — F5 + restart app banner vẫn hiện trên phiên mới; ledger runtime 0 row pending/processing; index production 0/262 document_id có vector; không sửa code, không bấm nút chuẩn bị lại, không merge `main`; commit `329524c` chỉ thêm 1 file báo cáo)
`ghi_chu`: 2026-09-30 ~12:31 +07 — Muse verdict ĐẠT, mailbox đặt `xong` (hết vé trong hàng chờ, không còn ticket trong kế hoạch cho máy này). Đề xuất hướng xử lý trong báo cáo (ẩn banner khi 0 nguồn đang bật; hoặc hiển thị tĩnh không nút hành động) chờ user quyết → vé fix riêng nếu cần.

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`) — user tự xóa nguồn vì trùng dữ liệu LSU máy nhà.
- Vé dieutra-banner-0494: **ĐẠT** 2026-09-30 ~12:31 +07 (commit `329524c`) — banner tái hiện sau F5 + restart app; ledger 0 row; 494 nguồn = 262 document_id, 0 có vector trong index production.
