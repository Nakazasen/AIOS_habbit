# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `LLM-ENABLE-DO-NHA-R1` — [NHÀ] cứu trợ vé đường AI ngoài sau escalate `cho-muse` 23:04 (giữ nguyên mục tiêu vé gốc: bật `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1`, đấu Nakazasen Router / Gemini Web, đo lại 6 câu L1–E3 so với lượt hodap-home lane cục bộ).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `bao_cao`: `docs/phieu-viec/ket-qua/llm-enable-do-nha.md`
- `ghi_chu` (điều phối Muse): 2026-10-02 23:09 +07 — **RESCUE sau escalate:** Phase A điều tra cho thấy từ 22:32 (mốc 0 kiểm công gate ĐẠT) đến 23:04 không có commit tiến triển nào, file báo cáo chưa tồn tại → escalate là hợp lệ. Viết lại vé thành R1 với 4 phase + checkpoint bắt buộc mỗi phase (cấm >45 phút không commit). Quyết định session: nếu session OMP cũ (PID 10792, từ 21:39) còn sống thì dừng ngay, chỉ một OMP chạy cho mailbox này. Vé gốc LLM-ENABLE-DO-NHA coi như bị thay thế, không quay lại bản cũ.
- `ghi_chu`: 2026-10-02 23:20 +07 — Phase 0: cầu nối Gemini `127.0.0.1:8585` = `direct_ready` (ưu tiên Router nhưng khóa env đã `unknown_error` ở mốc 21:55, local bridge đứng đầu thứ tự gọi). Đang chạy 1 câu L1 qua `synthesize_with_provider`. Tip `f1866e2`.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  1. `SPEED-COLDSTART-HOME` (`prompt-queue-speed-coldstart-home.md`) — **XẾP HÀNG SAU LLM-ENABLE-DO-NHA: nghiệm thu cold-start trên máy nhà (GPU) bằng lane 1 (Gemini) / lane 3 (Router) vì C-Agent ở nhà không dùng được; Phase 0 chốt trạng thái LLM-ENABLE-DO-NHA trước.**
  2. `KNOWLEDGE-ENRICH-PILOT` (`prompt-queue-knowledge-enrich-pilot.md`) — làm giàu tri thức theo lô bằng Copilot 365 (thí điểm 5 hiện tượng F CALL); form Q&A chuẩn + xuất/nhập batch + đo trước/sau. Đã bổ sung phụ lục: máy không có Copilot thì dùng Gemini Web qua cầu nối / Nakazasen Router soạn thảo, không dùng ChatGPT cá nhân cho dữ liệu công ty.
  3. `UX-CHAT-CORE` (`prompt-queue-ux-chat-core.md`) — [VM code + NHÀ verify] chat nhiều ý định trong một câu, nhúng log + vẽ biểu đồ ngay trong câu trả lời, lane tự động (hết đổi tay), hết báo lỗi ảo.
  4. `UX-INTERVIEW-FEEDBACK` (`prompt-queue-ux-interview-feedback.md`) — [VM code + NHÀ verify] phỏng vấn chuyên gia chạy được trong app + feedback theo từng gợi ý (sai/một phần bắt buộc nhập lý do, nguyên nhân thật, nội dung nắn lại) + vòng lặp tự cải thiện.
  5. `UX-AGENT-REPORT` (`prompt-queue-ux-agent-report.md`) — [VM code + NHÀ verify] agent tạo/sửa báo cáo (docx/pptx/md) bằng lệnh lời trong chat, có backup trước khi ghi đè.
