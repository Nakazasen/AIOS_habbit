# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: `SPEED-COLDSTART-HOME` — [NHÀ] nghiệm thu cold-start trên máy nhà (GPU) bằng lane 1 (Gemini qua cầu nối) / lane 3 (Nakazasen Router) vì C-Agent ở nhà không dùng được; Phase 0 chốt trạng thái LLM-ENABLE-DO-NHA trước.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `ghi_chu` (verdict Muse): 2026-10-02 23:35 +07 — **LLM-ENABLE-DO-NHA-R1 ĐẠT** (commit `2325065`, verify độc lập qua API: sha khớp, parent đúng, chỉ chạm báo cáo + trạng thái): đường gọi provider ngoài ĐẠT 6/6 câu qua cầu nối Gemini Web (`provider_used=true`, trace `valid`); Router Nakazasen lỗi khóa cloud nên rơi về cầu nối đúng như vé cho phép; SHA index trước/sau khớp `45eb0e07…65b7c0` (không ghi index). Chất lượng đáp án không đồng đều so với lane cục bộ — OMP ghi rõ, không fake PASS. Phát hành vé xếp hàng tiếp theo theo thứ tự đã duyệt.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  1. `KNOWLEDGE-ENRICH-PILOT` (`prompt-queue-knowledge-enrich-pilot.md`) — làm giàu tri thức theo lô bằng Copilot 365 (thí điểm 5 hiện tượng F CALL); form Q&A chuẩn + xuất/nhập batch + đo trước/sau. Đã bổ sung phụ lục: máy không có Copilot thì dùng Gemini Web qua cầu nối / Nakazasen Router soạn thảo, không dùng ChatGPT cá nhân cho dữ liệu công ty.
  2. `UX-CHAT-CORE` (`prompt-queue-ux-chat-core.md`) — [VM code + NHÀ verify] chat nhiều ý định trong một câu, nhúng log + vẽ biểu đồ ngay trong câu trả lời, lane tự động (hết đổi tay), hết báo lỗi ảo.
  3. `UX-INTERVIEW-FEEDBACK` (`prompt-queue-ux-interview-feedback.md`) — [VM code + NHÀ verify] phỏng vấn chuyên gia chạy được trong app + feedback theo từng gợi ý (sai/một phần bắt buộc nhập lý do, nguyên nhân thật, nội dung nắn lại) + vòng lặp tự cải thiện.
  4. `UX-AGENT-REPORT` (`prompt-queue-ux-agent-report.md`) — [VM code + NHÀ verify] agent tạo/sửa báo cáo (docx/pptx/md) bằng lệnh lời trong chat, có backup trước khi ghi đè.
