# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `e213f49` (điểm xuất phát sau pull; sẽ cập nhật SHA mới sau mỗi mốc)
- Báo cáo: chưa có (vé A đang làm)
- Ghi chú: OMP đã nhận vé A lúc 2026-09-27 13:36 +0700 (máy h410asrock); bắt đầu tìm tool integrity_check, chỉ đọc index.
- Cập nhật lần cuối: 2026-09-27 13:36 +0700 (OMP — nhận vé A)
