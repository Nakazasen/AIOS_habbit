# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: dieutra-banner-0494
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `13a403a`
`bao_cao`: `docs/phieu-viec/ket-qua/dieutra-banner-0494.md`
`ghi_chu`: 2026-09-30 12:26 +07 — da restart app (PID cu 1632 → moi 24812, cung lenh LAN 0.0.0.0:8501). Banner VAN CON nguyen: "0/494 tai lieu" + "494 tai lieu · 0 dang bat". Khong phai session Streamlit cu. Da chup 5 anh trong scratch/. Dang viet bao cao.

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`) — user tự xóa nguồn vì trùng dữ liệu LSU máy nhà.
- Vé này: điều tra banner "0/494 tài liệu" vẫn hiện sau khi xóa/tắt hết nguồn.
