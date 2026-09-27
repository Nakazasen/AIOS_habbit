# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `959a29c` (Vé B: GPU đã kiểm chứng; dry-run chỉ-đọc đang chạy)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 15:31 +0700 (máy h410asrock) — Runner tạm đã nạp ONNX Runtime GPU 1.28.0 với `CUDAExecutionProvider` đứng đầu session. Dry-run chỉ-đọc đang lập kế hoạch; chỉ mục chưa bị ghi. Sau khi đối chiếu số pending sẽ tạo bản sao lưu mới, xác minh `integrity_check=ok`, rồi mới resume theo lô batch 2.
- Cập nhật lần cuối: 2026-09-27 15:31 +0700 (OMP — dry-run GPU đang lập kế hoạch; chỉ mục chưa bị ghi)
