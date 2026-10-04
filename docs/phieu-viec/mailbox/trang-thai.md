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
- Vé audit/import ChatGPT enrichment (dedup + chấm M1–M5 + vòng sửa + import staging, tuyệt đối không nhập kho chính) CHƯA xếp — chờ user quyết có cho commit 45 file batch (1.998 cặp, có S/N và số đo sản xuất) lên repo public hay không.
- `commit`: 92bdab5
- `bao_cao`: 
- `ghi_chu`: 2026-10-04 13:14 +07 — Mã + test xong tại 92bdab5: composer tách 2 hàng (dòng mờ trạng thái/công tắc/mức tìm kiếm + hàng nút [+]/Hỏi), công tắc khối 4 lựa chọn mặc định Tự động, cờ `forced_domain` xuyên composer→adapter (ép khối bỏ qua cờ env, chặn tong_hop, thiếu kho thì báo rõ), dòng "Thư viện chung · 3 khối · luôn bật" gập sẵn ở sidebar, i18n 3 locale. Đang mở app thật để nghiệm thu + chụp ảnh.
