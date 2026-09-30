# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: hodap-lsu-loi
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: (cap nhat theo moc)
`bao_cao`: `docs/phieu-viec/ket-qua/hodap-lsu-loi.md`
`ghi_chu`: 2026-09-30 13:35 +07 — nhan ve (watcher mo 1/4), bat dau Pha 1 chan doan luong hoi dap trong so "Dieu tra loi LSU" (app dang chay PID 21016, cong 8501).

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`).
- Vé dieutra-banner-0494: **ĐẠT** 2026-09-30 ~12:31 +07 (commit `329524c`).
- Vé deploy-fix-banner-0494: **ĐẠT** 2026-09-30 ~12:58 +07 (commit `1b40e400`) — banner 0/494 đã ẩn, app LAN bình thường.
- Vé này: thông luồng hỏi đáp LSU + lỗi trên chat.
