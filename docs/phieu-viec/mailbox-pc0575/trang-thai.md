# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
- `ghi_chu` (tiến độ OMP): 2026-10-02 12:46 +07 — OMP nhận vé (watcher LAUNCH 1/4 lúc 12:43; điều kiện mở đã tới: verdict DEPLOY-BUOC05 **ĐẠT** + app CPU-only đang chạy `/_stcore/health`=ok). Bắt đầu đo tốc độ 6 câu L1–L3/E1–E3.
- Ticket hiện tại: `OPT-RAGV2-SPEED-APP-PC0575` — [CTY] đo tốc độ hỏi đáp app thật + hồ sơ nút thắt còn lại (phát hành 2026-10-02 sau verdict ĐẠT vé DEPLOY-BUOC05-PC0575).
- `prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
- `bao_cao`: `docs/phieu-viec/ket-qua/opt-ragv2-speed-app-pc0575.md`
- `ghi_chu`: 2026-10-02 — Muse verdict DEPLOY-BUOC05-PC0575: **ĐẠT** (6/6 B0–B5 chạy trên app thật CPU-only, B1-FEAT 1,6 s/câu ×3 mã, index production `e54c7745…` không đổi; LAN treo theo chỉ đạo 12:07 chờ admin/IT). Phát hiện 5.1 (ưu tiên action B3 bị `tra_cuu_loi_tuong_tu` cướp phrasing chuẩn, nguồn `b330020`): Muse tự vá trên VM, không giao OMP. Phát hành vé xếp hàng tiếp theo `OPT-RAGV2-SPEED-APP-PC0575` theo chỉ đạo 12:07.
- `hang-cho` (thứ tự do user duyệt 2026-10-01 ~16:45 +07):
  1. `hodap-lsu-loi-rerun` — **ĐÃ XONG, verdict ĐẠT 2026-10-01 ~18:07 +07**
  2. `OPT-RAGV2-PYLOOPS` — **ĐÃ XONG, verdict Muse ĐẠT 2026-10-02 ~09:26 +07**
  3. `OPT-RAGV2-LEXICAL` — **ĐÃ XONG, verdict Muse ĐẠT 2026-10-02 11:25 +07 (stretch <60s/câu chưa đạt, ghi rõ)**
  4. `DEPLOY-BUOC05-PC0575` — **ĐÃ XONG, verdict Muse ĐẠT 2026-10-02 (6/6 B0–B5 chạy thật; LAN treo chờ admin)**
  5. `OPT-RAGV2-SPEED-APP-PC0575` (`prompt-queue-opt-ragv2-speed-app-pc0575.md`) — **ĐANG PHÁT HÀNH (moi)**
