# Trạng thái mailbox

- Trạng thái: `moi`
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
- `commit`: (trống — chờ OMP nhận vé)
- `bao_cao`: (trống — chờ OMP nhận vé)
- `ghi_chu`: 2026-10-04 21:20 +07 — Muse verdict ROUND5-UX-COMPOSER: **ĐẠT**. Bằng chứng độc lập: commit 12f1744 (`fix(ux): clip attach label inside column + widen attach col at 1100px`) và 92bdab5 (`composer rows + knowledge block switch with forced-domain routing`) tồn tại trên nhánh; diff chỉ đụng `workspace_chat_app.py`/`workspace_chat_rag_v2_adapter.py`/`i18n.py` + test, không ghi index. Báo cáo OMP: ảnh live 5 file (composer 1440/1100, công tắc mở, LSU đã chọn, sidebar), số đo live 1100px (nút gắn nằm trọn khung, không tràn chữ), ép khối đủ 3 khối (LSU/Điều tra lỗi/MOM) + chặn `tong_hop`, sidebar 3 khối gập mặc định; compileall sạch, 3 file vé 81 pass + đúng 2 fail anti-hardcode đã biết, test ROUND5 93 pass, audit PASS, SHA tri_thuc không đổi 45eb0e07; full suite 3.994 pass/43 fail/19 error — cả 43+19 ngoài phạm vi vé (worker BGE không khởi động/đường dẫn WSL thiếu/thiếu gói graphifyy/ổ C đầy/venv). Giới hạn trung thực: chưa có ảnh câu hỏi thật kèm ép khối (tiến trình nền đang chạy) — đã chứng minh ở tầng định tuyến + test. Đã phát hành ROUTER-FIX (vé #1 hàng chờ theo lệnh user 19:05).
