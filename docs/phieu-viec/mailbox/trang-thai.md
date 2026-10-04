# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `ROUND5-UX-COMPOSER` — [NHÀ] sửa xô lệch composer + công tắc chọn khối tri thức. Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- `hang-cho` (Muse xếp 2026-10-04 16:15 +07 theo chỉ đạo "làm song song" của user; bổ sung 18:10 +07):
  1. `TOOL-1` (`prompt-queue-tool1.md`) — kiểm kê tool chưa nối vào chat (chỉ đọc + báo cáo, không sửa code). Role gợi ý: SMOL/TINY.
  2. `OMP-MODEL-REPORT` (`prompt-queue-omp-model-report.md`) — thợ OMP tự báo cáo model đang chạy (provider/model/mức/mapping roles). Role gợi ý: SMOL/TINY (~2 phút).
  3. `TOOL-2` (`prompt-queue-tool2.md`) — khung `chat_action`: tool đăng ký action → chat gọi theo ngữ cảnh, render giàu trong vùng trả lời. Role gợi ý: DEFAULT.
  4. `TOOL-3` (`prompt-queue-tool3.md`) — nối `mom_benchmark`, `rag_benchmark`, `rag_evaluator` vào chat qua khung TOOL-2. Role gợi ý: DEFAULT.
  5. `TOOL-4` (`prompt-queue-tool4.md`) — nối `expert_interview*`, `production_prediction`, `prediction_shadow_ui` vào chat. Role gợi ý: DEFAULT.
  6. `TOOL-5` (`prompt-queue-tool5.md`) — nối `visual_knowledge_map`, `knowledge_map_html`, `evidence_graph_viewer`, `worklens_semantic_map` vào chat. Role gợi ý: DEFAULT.
  7. `AUDIT-ENRICH-MOM` (`prompt-queue-audit-enrich-mom.md`) — audit 608 cặp MOM (sửa lỗi đã biết, numbering/format, dedup, chấm M1–M5, vòng sửa). Role gợi ý: DEFAULT.
  8. `AUDIT-ENRICH-LSU` (`prompt-queue-audit-enrich-lsu.md`) — audit 1.390 cặp LSU (dedup mạnh mẻ 39 + batch 999/0/--, chấm M1–M5, vòng sửa). Role gợi ý: DEFAULT.
  9. `IMPORT-STAGING-ENRICH` (`prompt-queue-import-staging-enrich.md`) — nhập cặp đã audit vào DB staging (không nhập kho chính), metric + smoke test. Role gợi ý: DEFAULT.
- Vé audit/import ChatGPT enrichment ĐÃ xếp (user duyệt commit batch lên repo public 2026-10-04 18:11 +07). Dữ liệu thô: `docs/phieu-viec/chatgpt-enrichment-raw/` (45 file, 1.998 cặp) — chỉ dùng để audit, không import trực tiếp.
- `commit`: 92bdab5
- `bao_cao`: 
- `ghi_chu`: 2026-10-04 18:55 +07 — Gate xong: composer/knowledge/domain 93 pass, audit PASS (PYTHONPATH=src), import app OK, 2 fail cũ đã biết đúng vé. Cổng watcher: đang làm thật, không cho-muse. Tiếp theo: mở app thật chụp ảnh nghiệm thu.
