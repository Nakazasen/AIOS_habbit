# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
- `ghi_chu` (tiến độ OMP): 2026-10-02 15:30 +07 — **C-Agent nối được từ PC0575** (`https://kdtvn-ai.cmcts.vn/...`, câu kiểm tra ngắn 14,4 s, trả lời OK). Đang chạy probe đầu-cuối đúng hàm app (`retrieve_workspace_chat_evidence` → `build_workspace_ai_prompt` → `call_cagent_prediction`) cho 6 câu, tách tìm kiếm/C-Agent viết/tổng (chế độ `AIOS_RAGV2_LEXICAL_V2=1`).
- `ghi_chu` (tiến độ OMP): 2026-10-02 15:15 +07 — Báo cáo chính đã viết xong (parity 100% cả 6 câu/2 chế độ, app as-deploy lỗi câu lạnh ~265 s, nút thắt eligibility + `chunks_fts`, index production không đổi) — nhưng vé có **bổ sung khẩn 13:21 về C-Agent**, OMP quay lại `dang-lam` để đo đường đầu-cuối C-Agent trên PC0575 trước khi chốt `xong-cho-duyet`.
- `ghi_chu` (điều phối Muse): 2026-10-02 13:21 +07 — **BỔ SUNG KHẨN THEO CHỐT CỦA USER:** chỉ máy công ty mới nối được AI C-Agent, phải tranh thủ đo ngay trong phiên này. OMP thêm đường đo đầu-cuối có C-Agent viết câu trả lời, tách thời gian tìm kiếm nội bộ / C-Agent viết / tổng người dùng chờ. Làm phần C-Agent sớm; nếu kẹt đăng nhập, mạng hoặc hạn mức thì báo đúng điểm kẹt, không bịa số.
- `ghi_chu` (tiến độ OMP): 2026-10-02 13:24 +07 — Init worker thật (đúng client + config app, qua subprocess ONNX) = **180,9 s** (dense preload 83,9 s + sparse 85,6 s) > 120 s ⇒ app không tự làm ấm kịp sau restart. Probe cùng pipeline đang chạy 6 câu v2off/v2on; L1 v2off = 86,3 s (eligibility 68,2 s + fts_match 12,7 s).
- `ghi_chu` (tiến độ OMP): 2026-10-02 13:12 +07 — Mốc as-deploy: 2 câu lạnh liên tiếp qua UI đều trả lỗi "AIOS đã tự làm nóng bộ đọc… chưa xong" sau ~265 s (worker init vượt cửa sổ 120 s của app). Đang đo init worker thật + probe cùng pipeline cho 6 câu (v2off/v2on).
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
  5. `OPT-RAGV2-SPEED-APP-PC0575` (`prompt-queue-opt-ragv2-speed-app-pc0575.md`) — **ĐANG LÀM (bổ sung khẩn C-Agent 13:21; báo cáo chính đã có, đang đo đầu-cuối C-Agent)**
