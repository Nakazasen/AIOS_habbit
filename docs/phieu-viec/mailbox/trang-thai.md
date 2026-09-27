# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `e808f24` (Vé B: dry-run GPU hoàn tất, đang xác minh bản sao lưu mới)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 15:34 +0700 (máy h410asrock) — Dry-run chỉ-đọc trên GPU xác nhận fingerprint `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`, 107.331 chunk truy xuất được, 8.328 đã có vector ONNX, 99.003 pending. Kế hoạch không ghi chỉ mục; đang tạo bản sao lưu sibling mới và chạy `integrity_check` đầy đủ trước khi resume batch 2.
- Cập nhật lần cuối: 2026-09-27 15:34 +0700 (OMP — dry-run GPU đạt fingerprint; chỉ mục chưa bị ghi)
