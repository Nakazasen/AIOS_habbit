# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `be31ea0` (Vé B: dry-run GPU đạt; bản sao lưu mới đang được tạo và kiểm tra)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 15:46 +0700 (máy h410asrock) — Dry-run chỉ-đọc xác nhận fingerprint `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`, 107.331 khối truy xuất được, 8.328 đã có vector ONNX, 99.003 còn thiếu. Tạo bản sao lưu bằng SQLite backup API và xác minh toàn vẹn đầy đủ đang chạy; chưa ghi chỉ mục.
- Cập nhật lần cuối: 2026-09-27 15:46 +0700 (OMP — đang tạo và kiểm tra bản sao lưu; chưa resume)
