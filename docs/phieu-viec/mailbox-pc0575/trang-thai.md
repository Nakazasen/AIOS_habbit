# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: dieutra-banner-0494
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `642e17a`
`bao_cao`: `docs/phieu-viec/ket-qua/dieutra-banner-0494.md`
`ghi_chu`: 2026-09-30 12:22 +07 — da tai hien banner tren trinh duyet that (moi hoan toan), F5 van con: "0/494 tai lieu" · "Quan ly tai lieu · 494 tai lieu · 0 dang bat". Ledger production = 0 row (16/20 trang free → tung co row bi xoa). Dang chuan bi restart app.

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`) — user tự xóa nguồn vì trùng dữ liệu LSU máy nhà.
- Vé này: điều tra banner "0/494 tài liệu" vẫn hiện sau khi xóa/tắt hết nguồn.
