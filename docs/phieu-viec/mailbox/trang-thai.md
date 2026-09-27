# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `13195df` (báo cáo Vé A)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 14:12 +0700 (máy h410asrock) — Vé A hoàn tất, đã đẩy báo cáo. Chỉ mục không đổi; không nhúng/resume. Bắt đầu khảo sát môi trường GPU cho Vé B.
- Cập nhật lần cuối: 2026-09-27 14:12 +0700 (OMP — hoàn tất Vé A, bắt đầu Vé B)
