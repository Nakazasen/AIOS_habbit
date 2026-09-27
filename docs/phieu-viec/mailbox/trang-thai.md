# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `ff9b612` (OMP xác nhận CUDA provider khả dụng)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 14:54 +0700 (máy h410asrock) — lần nạp session đầu rơi về CPU vì thiếu đường dẫn DLL `cublasLt64_12.dll`; không tính là chạy GPU. Đã thêm thư mục DLL vào `PATH`, nạp thử cuBLAS/cuDNN thành công. Chỉ mục chưa bị ghi; đang chạy đối chứng 20 chunk.
- Cập nhật lần cuối: 2026-09-27 14:54 +0700 (OMP — sửa đường dẫn DLL trong môi trường thử)
