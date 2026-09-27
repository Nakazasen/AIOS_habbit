# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `5d5200b` (OMP hoàn tất Vé A, bắt đầu khảo sát GPU)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 14:28 +0700 (máy h410asrock) — GTX 1060 3GB, driver 566.14 báo CUDA 12.7; `nvcc` không có. Cài môi trường thử riêng `onnxruntime-gpu 1.28.0` bản CUDA 12.8 + DLL CUDA/cuDNN; `CUDAExecutionProvider` khả dụng. VRAM trống 2.113 MiB, model ONNX fp32 trên đĩa 2.266.886.160 byte; đang thử tạo session batch nhỏ, chưa đụng chỉ mục.
- Cập nhật lần cuối: 2026-09-27 14:28 +0700 (OMP — GPU provider khả dụng, thử giới hạn VRAM)
