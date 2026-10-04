# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `ROUTER-FIX` — [NHÀ] chẩn đoán + sửa lỗi khóa cloud Router (`unknown_error` từ tối 2/10), verify 6 câu lạnh lane 3. Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `hang-cho` (còn lại sau khi phát hành ROUTER-FIX lúc 2026-10-04 21:20 +07; lịch sử xếp: Muse xếp 2026-10-04 16:15 +07 theo chỉ đạo "làm song song" của user; bổ sung 18:10 +07; đẩy ROUTER-FIX lên số 1 theo lệnh user 19:05 +07; chuyển TOOL-1 sang agy và AUDIT-ENRICH-MOM sang opencode 19:50 +07 để 3 thợ cùng làm):
  1. `OMP-MODEL-REPORT` (`prompt-queue-omp-model-report.md`) — thợ OMP tự báo cáo model đang chạy (provider/model/mức/mapping roles). Role gợi ý: SMOL/TINY (~2 phút).
  2. `TOOL-2` (`prompt-queue-tool2.md`) — khung `chat_action`: tool đăng ký action → chat gọi theo ngữ cảnh, render giàu trong vùng trả lời. Role gợi ý: DEFAULT.
  3. `TOOL-3` (`prompt-queue-tool3.md`) — nối `mom_benchmark`, `rag_benchmark`, `rag_evaluator` vào chat qua khung TOOL-2. Role gợi ý: DEFAULT.
  4. `TOOL-4` (`prompt-queue-tool4.md`) — nối `expert_interview*`, `production_prediction`, `prediction_shadow_ui` vào chat. Role gợi ý: DEFAULT.
  5. `TOOL-5` (`prompt-queue-tool5.md`) — nối `visual_knowledge_map`, `knowledge_map_html`, `evidence_graph_viewer`, `worklens_semantic_map` vào chat. Role gợi ý: DEFAULT.
  6. `AUDIT-ENRICH-LSU` (`prompt-queue-audit-enrich-lsu.md`) — audit LSU (dedup mạnh mẻ 39 + batch 999/0/--, chấm M1–M5, vòng sửa). Role gợi ý: DEFAULT. Lưu ý: vé vẫn ghi 1.390 cặp/Q2008, cập nhật lên số cuối trước khi chạy.
  7. `IMPORT-STAGING-ENRICH` (`prompt-queue-import-staging-enrich.md`) — nhập cặp đã audit vào DB staging (không nhập kho chính), metric + smoke test. Role gợi ý: DEFAULT.
- Vé audit/import ChatGPT enrichment ĐÃ xếp (user duyệt commit batch lên repo public 2026-10-04 18:11 +07). Dữ liệu thô: `docs/phieu-viec/chatgpt-enrichment-raw/` (45 file, 1.998 cặp) — chỉ dùng để audit, không import trực tiếp.
- `commit`: 1511955 (điểm nhận vé sau pull)
- `bao_cao`: (đang làm — chưa có)
- `ghi_chu`: 2026-10-04 21:42 +07 — OMP máy nhà đã nhận vé ROUTER-FIX, bắt đầu chẩn đoán unknown_error.
