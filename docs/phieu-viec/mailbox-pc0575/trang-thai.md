# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `dang-lam`
- `ghi_chu` (tiến độ OMP): 2026-10-02 17:58 +07 — OMP nhận vé (watcher LAUNCH 1/4 lúc 17:54; điều kiện mở đã tới: verdict SPEED-APP **ĐẠT** 15:47 + app CPU-only đang chạy `/_stcore/health`=ok, PID streamlit 19024). Bắt đầu Bước 1: đo chi tiết init worker 180,9 s; kế tiếp sửa warm-up đúng collection + đồng bộ cửa sổ chờ/giữ worker; cuối cùng đo lại 6 câu lạnh.
- `ghi_chu` (điều phối Muse): 2026-10-02 ~17:40 +07 — Phát hành vé xếp hàng #1 `SPEED-COLDSTART-PC0575` (copy `prompt-queue-speed-coldstart-pc0575.md` → `prompt.md`), `trang-thai` → `moi` theo hướng đi 17:39 (verdict OPT-RAGV2-SPEED-APP ĐẠT 15:47 đã có). Còn lại hàng chờ: `KNOWLEDGE-ENRICH-PILOT` (file vé nằm ở `docs/phieu-viec/mailbox/`, không có trong `mailbox-pc0575/`).
- `ghi_chu` (verdict Muse): 2026-10-02 15:47 +07 — **ĐẠT** (commit `a746693`). Đủ 5 tiêu chí vé: (1) số đo app thật PC0575, tách lạnh/ấm, không dùng số máy khác; (2) số đo C-Agent 6/6 câu 16,5–45,8 s, tách tìm kiếm/viết/tổng, có điểm kẹt app-UI→C-Agent báo đúng; (3) parity top-15 100% cả 6 câu/2 chế độ, E1 15/15 đúng thứ tự; (4) index production không đổi (SHA `e54c7745…` y nguyên), health `ok`; (5) hồ sơ nút thắt bằng số đo + EXPLAIN QUERY PLAN (eligibility 120.452 dòng + chunks_fts MATCH). Phát hiện chặn: câu RAG lạnh qua UI sau restart luôn lỗi ~265 s vì init worker thật 180,9 s > cửa sổ 120 s của app, đường warm-up dùng sai collection — đề xuất vé code tiếp theo (a) sửa warm-up/init, (b) tối ưu eligibility + FTS. Hàng chờ đã cạn (5/5 vé ĐẠT) → mailbox `xong`.
- `ghi_chu` (tiến độ OMP): 2026-10-02 15:40 +07 — **XONG (đã gồm phần C-Agent), chờ Muse duyệt**. Báo cáo: `docs/phieu-viec/ket-qua/opt-ragv2-speed-app-pc0575.md`. Điểm chính: parity **100% cả 6 câu/2 chế độ + E1 15/15**; app as-deploy **lỗi câu RAG lạnh sau restart** (~265 s) vì init worker thật **180,9 s > 120 s** (và warm-up dùng sai cấu hình); **C-Agent nối được, viết thành công 6/6 câu 16,5–45,8 s** (tổng đầu-cuối 79,9–292,5 s khi đĩa bận; app-UI chưa tới được bước C-Agent vì retrieval lạnh chặn trước); câu ấm khi đĩa rảnh 10–55 s (v2on 4/6 câu <60 s); nút thắt còn lại: quét eligibility 120.452 dòng + `chunks_fts MATCH` bm25; index production không đổi (`e54c7745…`), health `ok`.
- `ghi_chu` (tiến độ OMP): 2026-10-02 15:15 +07 — Báo cáo chính đã viết xong (parity 100% cả 6 câu/2 chế độ, app as-deploy lỗi câu lạnh ~265 s, nút thắt eligibility + `chunks_fts`, index production không đổi) — nhưng vé có **bổ sung khẩn 13:21 về C-Agent**, OMP quay lại `dang-lam` để đo đường đầu-cuối C-Agent trên PC0575 trước khi chốt `xong-cho-duyet`.
- `ghi_chu` (điều phối Muse): 2026-10-02 13:21 +07 — **BỔ SUNG KHẨN THEO CHỐT CỦA USER:** chỉ máy công ty mới nối được AI C-Agent, phải tranh thủ đo ngay trong phiên này. OMP thêm đường đo đầu-cuối có C-Agent viết câu trả lời, tách thời gian tìm kiếm nội bộ / C-Agent viết / tổng người dùng chờ. Làm phần C-Agent sớm; nếu kẹt đăng nhập, mạng hoặc hạn mức thì báo đúng điểm kẹt, không bịa số.
- `ghi_chu` (tiến độ OMP): 2026-10-02 13:24 +07 — Init worker thật (đúng client + config app, qua subprocess ONNX) = **180,9 s** (dense preload 83,9 s + sparse 85,6 s) > 120 s ⇒ app không tự làm ấm kịp sau restart. Probe cùng pipeline đang chạy 6 câu v2off/v2on; L1 v2off = 86,3 s (eligibility 68,2 s + fts_match 12,7 s).
- `ghi_chu` (tiến độ OMP): 2026-10-02 13:12 +07 — Mốc as-deploy: 2 câu lạnh liên tiếp qua UI đều trả lỗi "AIOS đã tự làm nóng bộ đọc… chưa xong" sau ~265 s (worker init vượt cửa sổ 120 s của app). Đang đo init worker thật + probe cùng pipeline cho 6 câu (v2off/v2on).
- `ghi_chu` (tiến độ OMP): 2026-10-02 12:46 +07 — OMP nhận vé (watcher LAUNCH 1/4 lúc 12:43; điều kiện mở đã tới: verdict DEPLOY-BUOC05 **ĐẠT** + app CPU-only đang chạy `/_stcore/health`=ok). Bắt đầu đo tốc độ 6 câu L1–L3/E1–E3.
- Ticket hiện tại: `SPEED-COLDSTART-PC0575` — [CTY] sửa câu hỏi lạnh qua UI ~265 s (bộ đọc khởi động 180,9 s > cửa sổ 120 s của app; warm-up làm nóng nhầm collection).
- `prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
- `bao_cao`: `docs/phieu-viec/ket-qua/opt-ragv2-speed-app-pc0575.md`
- `ghi_chu`: 2026-10-02 — Muse verdict DEPLOY-BUOC05-PC0575: **ĐẠT** (6/6 B0–B5 chạy trên app thật CPU-only, B1-FEAT 1,6 s/câu ×3 mã, index production `e54c7745…` không đổi; LAN treo theo chỉ đạo 12:07 chờ admin/IT). Phát hiện 5.1 (ưu tiên action B3 bị `tra_cuu_loi_tuong_tu` cướp phrasing chuẩn, nguồn `b330020`): Muse tự vá trên VM, không giao OMP. Phát hành vé xếp hàng tiếp theo `OPT-RAGV2-SPEED-APP-PC0575` theo chỉ đạo 12:07.
- `hang-cho` (thứ tự do user duyệt 2026-10-01 ~16:45 +07):
  1. `hodap-lsu-loi-rerun` — **ĐÃ XONG, verdict ĐẠT 2026-10-01 ~18:07 +07**
  2. `OPT-RAGV2-PYLOOPS` — **ĐÃ XONG, verdict Muse ĐẠT 2026-10-02 ~09:26 +07**
  3. `OPT-RAGV2-LEXICAL` — **ĐÃ XONG, verdict Muse ĐẠT 2026-10-02 11:25 +07 (stretch <60s/câu chưa đạt, ghi rõ)**
  4. `DEPLOY-BUOC05-PC0575` — **ĐÃ XONG, verdict Muse ĐẠT 2026-10-02 (6/6 B0–B5 chạy thật; LAN treo chờ admin)**
  5. `OPT-RAGV2-SPEED-APP-PC0575` (`prompt-queue-opt-ragv2-speed-app-pc0575.md`) — **ĐÃ XONG (gồm bổ sung khẩn C-Agent), verdict Muse ĐẠT 2026-10-02 ~15:47 +07**

## 2026-10-02 ~17:39 +07 — Chốt hướng đi tiếp theo (Muse quyết theo ủy quyền "đừng bắt tao quyết định")

**Hướng đi (theo thứ tự ưu tiên):**

1. **[CTY] `SPEED-COLDSTART-PC0575`** — câu hỏi lạnh qua UI ~265 giây (bộ đọc khởi động 180,9 giây > cửa sổ 120 giây của app, warm-up làm nóng nhầm collection). User chốt tốc độ phản hồi là ưu tiên số 1 → đây là việc tiếp theo phải làm. Vé `prompt-queue-speed-coldstart-pc0575.md` đã phát hành, đứng ĐẦU hàng chờ.
2. **[CTY] `KNOWLEDGE-ENRICH-PILOT`** — pilot làm giàu tri thức 5 hiện tượng F CALL thật: bộ sinh câu hỏi vàng AIOS → file batch cho Copilot → ghi đáp án vào staging với nhãn `kiến thức đã được đào tạo bổ sung`. Đứng thứ 2 trong hàng chờ.
3. **[VM] Muse tự code (song song, không chờ OMP):** schema form chuẩn + bộ sinh/chấm điểm câu hỏi vàng + exporter batch JSONL/Markdown + importer vào staging + bộ đo chất lượng trước/sau — cho pilot và cho feedback theo từng gợi ý/câu trả lời (nợ sau demo).
4. **[NHÀ] `LLM-ENABLE-DO-NHA`** vẫn `dang-lam`, chờ báo cáo `xong-cho-duyet` — khi xong mới xếp vé verify và J3 [NGƯỜI DÙNG] (đã phát hành lại nguyên văn, bản sao bền ở `~/workspace/aios_mailbox_backup/`).

**Nguyên tắc:** Muse ôm việc nền song song trên VM, không ngồi chờ OMP/user; OMP chỉ làm hàng chờ mailbox; J3 chờ user nên để sau.

- `hang-cho` (mới, 2026-10-02 ~17:39):
  1. `KNOWLEDGE-ENRICH-PILOT` (`docs/phieu-viec/mailbox/prompt-queue-knowledge-enrich-pilot.md`) — [CTY] pilot làm giàu tri thức 5 hiện tượng F CALL (Copilot → staging, nhãn `kiến thức đã được đào tạo bổ sung`) — (vé #1 `SPEED-COLDSTART-PC0575` đã phát hành 17:40)