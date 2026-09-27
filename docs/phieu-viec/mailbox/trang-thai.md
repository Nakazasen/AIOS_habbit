# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `04056ab` (Vé B: kiểm tra GPU 20 chunk đạt; đang chuẩn bị dry-run, sao lưu mới và tiếp tục theo lô)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 15:14 +0700 (máy h410asrock) — ONNX Runtime GPU 1.28.0 trên CUDA 12.8 đã chạy GPU thật; 20 chunk có fingerprint đúng, cosine CPU/GPU và GPU/vector lưu đều 1.0. Batch 2 nhanh nhất trong các mẻ thử (25,2 lần so với CPU); batch 20 là mẻ lớn nhất đã thử. VRAM đỉnh 2.833/3.072 MiB. Mã nguồn hiện vẫn chọn CPU cố định, nên phần áp dụng sẽ dùng runner tạm trong môi trường GPU riêng, không sửa mã nguồn; trước khi ghi phải dry-run và tạo bản sao lưu mới có `integrity_check=ok`.
- Cập nhật lần cuối: 2026-09-27 15:14 +0700 (OMP — đối chứng GPU 20 chunk thành công; chưa ghi chỉ mục)
