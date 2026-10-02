# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: `LLM-ENABLE-DO-NHA` — [NHÀ] bật `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS=1`, đấu đường AI ngoài (Nakazasen Router / Gemini Web), đo lại 6 câu L1–E3 và so với lượt hodap-home chạy lane cục bộ.
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `bao_cao`: `docs/phieu-viec/ket-qua/llm-enable-do-nha.md`
- `ghi_chu`: 2026-10-02 06:51 +07 OMP nhận vé (watcher LAUNCH 1/4 lúc 06:43; điều kiện mở đã tới: cầu nối Gemini Web `127.0.0.1:8585` = `direct_ready`, khóa provider sẵn có ở mức user). Bắt đầu kiểm chứng đường AI ngoài cho lane tổng hợp RAG v2.
- `hang-cho` (thứ tự do user duyệt 2026-10-02 ~17:34 +07):
  1. `KNOWLEDGE-ENRICH-PILOT` (`prompt-queue-knowledge-enrich-pilot.md`) — **XẾP HÀNG SAU LLM-ENABLE-DO-NHA: làm giàu tri thức theo lô bằng Copilot 365 (thí điểm 5 hiện tượng F CALL); form Q&A chuẩn + xuất/nhập batch + đo trước/sau.**
