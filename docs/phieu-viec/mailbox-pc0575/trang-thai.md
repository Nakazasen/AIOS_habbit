# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong-cho-duyet`
Ticket hiện tại: dieutra-banner-0494
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `329524c`
`bao_cao`: `docs/phieu-viec/ket-qua/dieutra-banner-0494.md`
`ghi_chu`: 2026-09-30 12:34 +07 — xong cho Muse duyet. Banner tai hien tren phien trinh duyet moi, van con sau F5 va sau restart app (PID 1632 → 24812). Ledger runtime production = 0 row (khong co pending/processing nao). 494 nguon = 494 tai lieu so "Dieu tra loi LSU" (khong phai nguon tam); 0/262 document_id co vector trong index production. KHONG sua code, KHONG bam nut chuan bi lai. Anh chup trong scratch/ (git-ignore).

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`) — user tự xóa nguồn vì trùng dữ liệu LSU máy nhà.
- Vé này: điều tra banner "0/494 tài liệu" vẫn hiện sau khi xóa/tắt hết nguồn.
