# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `xong-cho-duyet`
Ticket hiện tại: deploy-fix-banner-0494
`prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
`commit`: `68bd5a0`
`bao_cao`: `docs/phieu-viec/ket-qua/deploy-fix-banner-0494.md`
`ghi_chu`: 2026-09-30 12:53 +07 — XONG cho Muse duyet. Pull fast-forward `8611f9a..7e9181e`: HEAD = `7e9181e`, fix `e5d37fc` la ancestor (fix da co tren may; code tren dia dong 4661 = `tracked_prep_sources = enabled_ctx_sources`, khong con fallback). Da dung app cu (PID 24812/18664, boot 12:23:03 — chay code TRUOC fix) va restart bang `scratch/p5_run_lan.ps1`: app moi PID 21016 boot 12:47:03, listen `0.0.0.0:8501`, HTTP 200 (localhost + 192.168.1.41), `/_stcore/health` = ok. Verify so "Dieu tra loi LSU" (494 tai lieu, 0 nguon dang bat): banner "0/494" + nut "Tiep tuc" KHONG con — dung tren phien thuong, sau F5, va tren phien trinh duyet moi hoan toan; 19 nut tren trang khong co nut nao thuoc nhom cam. Ledger khong doi (mtime 12:08:39, 0 row) → khong enqueue gi. Anh chup trong `scratch/` (git-ignore). KHONG bam nut chuan bi lai nao.

Mốc:
- 2026-09-30 12:45 +07 — Nhận ticket. `git pull` nhánh `phieu-viec/rag-fix1`: HEAD = `7e9181e`, fix `e5d37fc` là ancestor (fix đã có trên máy). [commit `961f8f4`]
- 2026-09-30 12:48 +07 — Đã dừng app cũ (PID 24812/18664 chạy code TRƯỚC fix, boot 12:23) và restart bằng `scratch/p5_run_lan.ps1`: app mới PID 21016 listen `0.0.0.0:8501`, HTTP 200 (localhost + `192.168.1.41`), `/_stcore/health` = `ok`. [commit `17c350a`]
- 2026-09-30 12:53 +07 — Verify xong (banner ẩn trên phiên thường + F5 + phiên mới; ledger không đổi; LAN HTTP 200). Báo cáo + trạng thái `xong-cho-duyet`. [commit `68bd5a0`]

Lịch sử:
- P5 (deploy model ONNX + mở LAN) **ĐẠT** 2026-09-30 ~09:5x +07 (commit `97207d5`).
- P5b (kiểm tra lại truy cập trên mạng mới) **ĐẠT** 2026-09-30 ~11:1x +07 (commit `5e049a5f`); user xác nhận thiết bị khác vào được app qua LAN (commit `b854cd8`).
- Vé chuan-bi-tai-lieu-lsu: **HỦY** theo lệnh user 2026-09-30 ~11:54 +07 (commit `63cc350`).
- Vé dieutra-banner-0494: **ĐẠT** 2026-09-30 ~12:31 +07 (commit `329524c`).
- Vé này (deploy-fix-banner-0494): xong-chờ-duyệt — pull `e5d37fc` + restart app + verify banner đã ẩn, LAN vẫn phục vụ.
