# Trạng thái mailbox

- Trạng thái: `xong-cho-duyet`
- Ticket hiện tại: Vé P1.4 — B1–B5 smoke test kho production (tuyến nội bộ).
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `commit`: fdf919e
- `bao_cao`: `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`
- `ghi_chu`: 2026-09-29 01:05 +07 (h410asrock) — ĐẠT 4 tiêu chí vé. B1/B2/B3/B5 chạy xong không lỗi/timeout (50,8/18,2/19,6/21,9s), B4 chạy đủ (39,6s, loại khỏi chấm). Câu trả lời grounded, `provider_used=false`, mode `local_extractive`; không provider nào được cấu hình. Không ghi D: diff gốc dữ liệu 0 thay đổi + SHA index D sau chạy vẫn `062ec090…`. Không rời máy: 43 mẫu mạng trong truy vấn = 0 kết nối. Cần Muse biết 3 điểm: (1) worker tự dựng provider cloud từ env máy và đã thử gọi ở lượt nháp — đã chặn bằng blank khóa + guard; (2) 422/496 document stale nên chỉ 74 document truy vấn được ở chế độ read-only; (3) B5 có bằng chứng định nghĩa HOUSE_METHOD nhưng câu trả lời extractive không chọn dòng đó.
- Ticket trước: P1.3 — sao lưu + chép kho production ĐẠT, B1–B5 chưa chạy (báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md`).
