# Trạng thái mailbox — KDTVN-PC0575

Trạng thái: `moi`
- Ticket hiện tại: `OPT-RAGV2-LEXICAL` — [VM→CTY] tối ưu khâu lexical + sửa token cache bị vô hiệu giữa query; OMP verify trên PC0575 CPU-only (Phase A code `4a796ac` + Phase B code `1f30092` đã có trên VM, chờ verify sau verdict PYLOOPS).
- `prompt`: `docs/phieu-viec/mailbox-pc0575/prompt.md`
- `bao_cao`: `docs/phieu-viec/ket-qua/opt-ragv2-pyloops.md` (mục 8 — OMP verify PC0575)
- `ghi_chu`: 2026-10-02 ~09:26 +07 — **Muse verdict PYLOOPS: ĐẠT để đóng vé.** Lý do: test vé 18/18 + gộp 80 passed trên PC0575, index production không đổi (mtime 15:46:42 01/10), parity top-15: 5/6 trùng 100% từng vị trí; E1 đủ 15/15 chunk, chỉ hoán vị #10↔#11 trong dải đồng hạng RRF 3,0 (13 vị trí tie) và `AIOS_RAG_V2_CJK_PREFILTER=0` trả đúng baseline — chấp nhận tie-order này, không coi là lệch ngữ nghĩa. **Mốc query lạnh <60s CHƯA đạt (266,2s)** — nguyên nhân đã chứng minh: bảng tạm FTS5 đổi `total_changes` làm cache dense/sparse mất giữa query non-CJK; fix đã có ở Phase A vé LEXICAL (`4a796ac`). Vé LEXICAL là nơi verify lại mốc này; không tuyên bố PYLOOPS đạt tốc độ.
- `ghi_chu`: 2026-10-02 ~09:43 +07 — **Demo bổ sung (giữ lại từ lượt trước, chưa xong hẳn):** nạp nguyên file `IRIS_LSU_BOWSKEW_4_2026_08_Sub.csv` 14,8s, `da_ghi=50.000`, `bi_cat=1.141.207`; đổi người nhận cảnh báo thật sang `vinh.bd@dtvn.kyocera.com`, thư kiểm tra qua sink cục bộ PASS (101.625 B kèm PNG), **gửi thật qua `smtp.office365.com:587` KHÔNG được ở bước đăng nhập (server đóng/timeout) — thư CHƯA tới hộp thật; trước demo bấm Gửi cần kiểm SMTP AUTH/mạng Wi-Fi `KT_CHETAO`.** File `C:/tmp/b0-dict/error_cases_dict.db` vẫn chưa có (kiểm 09:41) — chưa đối chiếu SHA `6bd41a8c…2369`/chưa trỏ `AIOS_ERROR_CASES_DB`. App LAN health `ok`, sẵn sàng demo 10:00 trên chính PC0575.
- `hang-cho` (thứ tự do user duyệt 2026-10-01 ~16:45 +07):
  1. `hodap-lsu-loi-rerun` — **ĐÃ XONG, verdict ĐẠT 2026-10-01 ~18:07 +07**
  2. `OPT-RAGV2-PYLOOPS` — **ĐÃ XONG, verdict Muse ĐẠT 2026-10-02 ~09:26 +07 (đóng vé; mốc <60s chuyển sang LEXICAL verify)**
  3. `OPT-RAGV2-LEXICAL` (`prompt-queue-opt-ragv2-lexical.md`) — **ĐANG PHÁT HÀNH (moi)**
  4. `DEPLOY-BUOC05-PC0575` (`prompt-queue-deploy-buoc05-pc0575.md`) — phát hành sau khi track OPT (vé 2 → vé 3) có verdict cuối **và** B5 verdict ĐẠT trên máy nhà (B5 đã ĐẠT 2026-10-01 ~17:50 +07)
