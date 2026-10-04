# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `TOOL-2` — [NHÀ] khung `chat_action`: tool đăng ký action → chat gọi theo ngữ cảnh, render giàu trong vùng trả lời. Prompt: `docs/phieu-viec/mailbox/prompt.md`. Role gợi ý: DEFAULT. Không ghi index, chỉ code + test.
- `hang-cho` (còn lại sau khi phát hành TOOL-2 lúc 2026-10-04 23:41 +07; lịch sử xếp: Muse xếp 2026-10-04 16:15 +07 theo chỉ đạo "làm song song" của user; bổ sung 18:10 +07; đẩy ROUTER-FIX lên số 1 theo lệnh user 19:05 +07; chuyển TOOL-1 sang agy và AUDIT-ENRICH-MOM sang opencode 19:50 +07 để 3 thợ cùng làm; ROUTER-FIX ĐẠT 23:06 +07 → phát hành OMP-MODEL-REPORT; OMP-MODEL-REPORT ĐẠT 23:41 +07 → phát hành TOOL-2):
  1. `TOOL-3` (`prompt-queue-tool3.md`) — nối `mom_benchmark`, `rag_benchmark`, `rag_evaluator` vào chat qua khung TOOL-2. Role gợi ý: DEFAULT.
  2. `TOOL-4` (`prompt-queue-tool4.md`) — nối `expert_interview*`, `production_prediction`, `prediction_shadow_ui` vào chat. Role gợi ý: DEFAULT.
  3. `TOOL-5` (`prompt-queue-tool5.md`) — nối `visual_knowledge_map`, `knowledge_map_html`, `evidence_graph_viewer`, `worklens_semantic_map` vào chat. Role gợi ý: DEFAULT.
  4. `AUDIT-ENRICH-LSU` — CHUYỂN cho opencode 22:45 +07 (opencode đã ĐẠT vé LSU 22:50; đang làm IMPORT-STAGING-ENRICH).
  5. `IMPORT-STAGING-ENRICH` — CHUYỂN cho opencode 22:55 +07 (cả 2 audit ĐẠT, đủ điều kiện chạy; opencode đang làm, mốc-1 rào-staging ĐẠT).
- Vé audit/import ChatGPT enrichment ĐÃ xếp (user duyệt commit batch lên repo public 2026-10-04 18:11 +07). Dữ liệu thô: `docs/phieu-viec/chatgpt-enrichment-raw/` (45 file, 1.998 cặp) — chỉ dùng để audit, không import trực tiếp.
- `commit`: `e60e621` (phát hành vé TOOL-2)
- `bao_cao`: `docs/phieu-viec/ket-qua/omp-model-report.md`
- `ghi_chu` (verdict Muse): 2026-10-04 ~23:41 +07 — **ĐẠT** vé `OMP-MODEL-REPORT` (tích tạm, chờ user nghiệm thu). Kiểm chứng độc lập qua GitHub API: diff `4a83762` chỉ +44/-0 báo cáo `omp-model-report.md` và +2/-2 `trang-thai.md`, không code, không secret, không merge `main`. Báo cáo đủ spec vé: đọc trực tiếp `C:/Users/Admin/.omp/agent/config.yml` (55 dòng), liệt kê đầy đủ ánh xạ roles (default/smol/tiny/plan/advisor/...) + chuỗi fallback. **Thay đổi đáng chú ý:** DEFAULT hiện là `commandcode/meta/muse-spark-1.3-contributor:xhigh` (khác ghi chú OMP 02/10: `xai-oauth/grok-4.7:medium` — OMP đã đổi cấu hình, không phải Muse).
- `ghi_chu`: 2026-10-04 23:47 +07 — OMP mốc-1 khảo sát xong: TOOL-2 đã làm 30/09 (verdict ĐẠT 589d8fe), khung chat_action + tool mẫu + cờ tắt vẫn còn trong HEAD; TOOL-3/4/5 cũng đã xong sau đó. Hướng xử lý: không viết lại code, chỉ kiểm tra lại đúng 4 bước vé rồi báo cáo.
