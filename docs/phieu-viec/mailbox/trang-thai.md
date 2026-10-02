# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `SPEED-COLDSTART-HOME` — [NHÀ] nghiệm thu cold-start trên máy nhà (GPU) bằng lane 1 (Gemini qua cầu nối) / lane 3 (Nakazasen Router) vì C-Agent ở nhà không dùng được; Phase 0 chốt trạng thái LLM-ENABLE-DO-NHA trước.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `ghi_chu`: 2026-10-02 23:48 +07 — cổng gate ĐẠT (RELAUNCH 1/4, không cho-muse). Lane 1 `direct_ready` cổng 8585. Init lạnh worker persist đã xong: PID 11896, ONNX, init 112,1 s (nạp model 39,3 s). Tiếp 3 lần gắn lại + 6 câu lạnh. Không ghi index.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  1. `KNOWLEDGE-ENRICH-PILOT` (`prompt-queue-knowledge-enrich-pilot.md`) — làm giàu tri thức theo lô bằng Copilot 365 (thí điểm 5 hiện tượng F CALL); form Q&A chuẩn + xuất/nhập batch + đo trước/sau. Đã bổ sung phụ lục: máy không có Copilot thì dùng Gemini Web qua cầu nối / Nakazasen Router soạn thảo, không dùng ChatGPT cá nhân cho dữ liệu công ty.
  2. `UX-CHAT-CORE` (`prompt-queue-ux-chat-core.md`) — [VM code + NHÀ verify] chat nhiều ý định trong một câu, nhúng log + vẽ biểu đồ ngay trong câu trả lời, lane tự động (hết đổi tay), hết báo lỗi ảo.
  3. `UX-INTERVIEW-FEEDBACK` (`prompt-queue-ux-interview-feedback.md`) — [VM code + NHÀ verify] phỏng vấn chuyên gia chạy được trong app + feedback theo từng gợi ý (sai/một phần bắt buộc nhập lý do, nguyên nhân thật, nội dung nắn lại) + vòng lặp tự cải thiện.
  4. `UX-AGENT-REPORT` (`prompt-queue-ux-agent-report.md`) — [VM code + NHÀ verify] agent tạo/sửa báo cáo (docx/pptx/md) bằng lệnh lời trong chat, có backup trước khi ghi đè.
