# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `OMP-MODEL-REPORT` — [NHÀ] thợ OMP tự báo cáo model đang chạy (provider/model/mức/mapping roles). Prompt: `docs/phieu-viec/mailbox/prompt.md`. Role gợi ý: SMOL/TINY (~2 phút). Không code.
- `hang-cho` (còn lại sau khi phát hành OMP-MODEL-REPORT lúc 2026-10-04 23:06 +07; lịch sử xếp: Muse xếp 2026-10-04 16:15 +07 theo chỉ đạo "làm song song" của user; bổ sung 18:10 +07; đẩy ROUTER-FIX lên số 1 theo lệnh user 19:05 +07; chuyển TOOL-1 sang agy và AUDIT-ENRICH-MOM sang opencode 19:50 +07 để 3 thợ cùng làm; ROUTER-FIX ĐẠT 23:06 +07 → phát hành vé xếp hàng #1 OMP-MODEL-REPORT):
  1. `TOOL-2` (`prompt-queue-tool2.md`) — khung `chat_action`: tool đăng ký action → chat gọi theo ngữ cảnh, render giàu trong vùng trả lời. Role gợi ý: DEFAULT.
  2. `TOOL-3` (`prompt-queue-tool3.md`) — nối `mom_benchmark`, `rag_benchmark`, `rag_evaluator` vào chat qua khung TOOL-2. Role gợi ý: DEFAULT.
  3. `TOOL-4` (`prompt-queue-tool4.md`) — nối `expert_interview*`, `production_prediction`, `prediction_shadow_ui` vào chat. Role gợi ý: DEFAULT.
  4. `TOOL-5` (`prompt-queue-tool5.md`) — nối `visual_knowledge_map`, `knowledge_map_html`, `evidence_graph_viewer`, `worklens_semantic_map` vào chat. Role gợi ý: DEFAULT.
  5. `AUDIT-ENRICH-LSU` — CHUYỂN cho opencode 22:45 +07 (opencode đã ĐẠT vé LSU 22:50; đang làm IMPORT-STAGING-ENRICH).
  6. `IMPORT-STAGING-ENRICH` — CHUYỂN cho opencode 22:55 +07 (cả 2 audit ĐẠT, đủ điều kiện chạy; opencode đang làm, mốc-1 rào-staging ĐẠT).
- Vé audit/import ChatGPT enrichment ĐÃ xếp (user duyệt commit batch lên repo public 2026-10-04 18:11 +07). Dữ liệu thô: `docs/phieu-viec/chatgpt-enrichment-raw/` (45 file, 1.998 cặp) — chỉ dùng để audit, không import trực tiếp.
- `commit`: `f37fe1d` (điểm nhận vé sau pull)
- `bao_cao`: (đang làm — chưa có)
- `ghi_chu`: 2026-10-04 23:25 +07 — OMP máy nhà đã nhận vé OMP-MODEL-REPORT, máy `h410asrock`, OMP đang chạy, bắt đầu đọc cấu hình model.
