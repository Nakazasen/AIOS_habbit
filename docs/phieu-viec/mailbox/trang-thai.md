# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `LLM-ENABLE-DO-NHA` — [NHÀ] bật `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1`, đấu đường AI ngoài (Nakazasen Router / Gemini Web), đo lại 6 câu L1–E3 và so với lượt hodap-home chạy lane cục bộ.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `bao_cao`: `docs/phieu-viec/ket-qua/llm-enable-do-nha.md`
- `ghi_chu`: 2026-10-02 21:55 +07 OMP phiên RELAUNCH 3/4 (lúc 21:39). Kiểm cổng gate ĐẠT — điều kiện mở đã tới: Cầu nối Gemini Web `127.0.0.1:8585` tự bật OK = `direct_ready`, thử 1 câu ra đáp án thật; khóa provider env lỗi `unknown_error` nên chọn Cầu nối Gemini Web theo thứ tự vé. Bắt đầu dựng probe đấu bridge vào lane tổng hợp RAG v2 (`AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1` + `AIOS_LOCAL_AI_ENDPOINT`).
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~22:05 +07):
  1. `SPEED-COLDSTART-HOME` (`prompt-queue-speed-coldstart-home.md`) — **XẾP HÀNG SAU LLM-ENABLE-DO-NHA: nghiệm thu cold-start trên máy nhà (GPU) bằng lane 1 (Gemini) / lane 3 (Router) vì C-Agent ở nhà không dùng được; Phase 0 chốt trạng thái LLM-ENABLE-DO-NHA trước.**
  2. `KNOWLEDGE-ENRICH-PILOT` (`prompt-queue-knowledge-enrich-pilot.md`) — làm giàu tri thức theo lô bằng Copilot 365 (thí điểm 5 hiện tượng F CALL); form Q&A chuẩn + xuất/nhập batch + đo trước/sau. Đã bổ sung phụ lục: máy không có Copilot thì dùng Gemini Web qua cầu nối / Nakazasen Router soạn thảo, không dùng ChatGPT cá nhân cho dữ liệu công ty.
  3. `UX-CHAT-CORE` (`prompt-queue-ux-chat-core.md`) — [VM code + NHÀ verify] chat nhiều ý định trong một câu, nhúng log + vẽ biểu đồ ngay trong câu trả lời, lane tự động (hết đổi tay), hết báo lỗi ảo.
  4. `UX-INTERVIEW-FEEDBACK` (`prompt-queue-ux-interview-feedback.md`) — [VM code + NHÀ verify] phỏng vấn chuyên gia chạy được trong app + feedback theo từng gợi ý (sai/một phần bắt buộc nhập lý do, nguyên nhân thật, nội dung nắn lại) + vòng lặp tự cải thiện.
  5. `UX-AGENT-REPORT` (`prompt-queue-ux-agent-report.md`) — [VM code + NHÀ verify] agent tạo/sửa báo cáo (docx/pptx/md) bằng lệnh lời trong chat, có backup trước khi ghi đè.
