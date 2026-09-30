# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
Ticket hiện tại: deploy-fix-banner-0494
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `961f8f4` (mốc nhận việc)
`bao_cao`: `docs/phieu-viec/ket-qua/deploy-fix-banner-0494.md` (chưa tạo)

Mốc:
- 2026-09-30 12:45 +07 — Nhận ticket. `git pull` nhánh `phieu-viec/rag-fix1`: HEAD = `7e9181e`, fix `e5d37fc` là ancestor (fix đã có trên máy). [commit `961f8f4`]
- 2026-09-30 12:48 +07 — Đã dừng app cũ (PID 24812/18664 chạy code TRƯỚC fix, boot 12:23) và restart bằng `scratch/p5_run_lan.ps1`: app mới PID 21016 listen `0.0.0.0:8501`, HTTP 200 (localhost + `192.168.1.41`), `/_stcore/health` = `ok`. Bước kế: mở sổ "Điều tra lỗi LSU" verify banner đã ẩn.

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`).
- Vé dieutra-banner-0494: **ĐẠT** 2026-09-30 ~12:31 +07 (commit `329524c`).
- Vé này: deploy fix banner (pull e5d37fc + restart app + verify).
