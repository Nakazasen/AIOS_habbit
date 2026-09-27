# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Vé KHẨN — Dừng P1.3; commit 3 fix retrieval + push ngay (lệnh user 06:51 +07)
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `ghi_chu`: 2026-09-28 ~06:58 +07 (Muse VM) — Sửa sự cố commit d2e2458: commit này vô tình revert trang-thai.md về nội dung 05:55 (và chưa viết prompt vé KHẨN), làm mất ghi chú 06:45 của OMP. Khôi phục tại đây: OMP 06:45 +07 báo P1.3 dừng ở bước B1–B5 (báo cáo ở commit b196d38 "document safe-route blockers"); OMP chặn vì (1) chưa rõ tuyến trả lời cho B1–B5 khi cầu nối Gemini Web direct_ready nhưng quy tắc cấm local_only ra ngoài, C-AGENT cần user chọn rõ; (2) runtime_root production vẫn nằm trên ổ D — cần cách bảo đảm scheduler không ghi thêm lên D. Đã xong an toàn trước khi dừng: backup D→C 32452608 byte, SHA-256 khớp file D cũ, quick_check=ok; nguồn canary 2552659968 byte, quick_check=ok.
- Ticket trước: Vé P1.3 — DỪNG GIỮA CHỪNG theo lệnh user (đã xong backup + copy nguồn, SHA khớp; chưa chạy B1–B5); báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md`.
