# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `c708dc1` (Vé B: bản sao lưu mới đạt `integrity_check=ok`; bắt đầu tiếp tục bằng GPU, mẻ 2)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 15:53 +0700 (máy h410asrock) — Bản sao lưu sibling `library.sqlite.bak-20260927-153511-g1gpu` đã vượt kiểm tra `integrity_check=ok`; kích thước bản sao và chỉ mục đều 1.698.164.736 byte, mtime chỉ mục không đổi. Dry-run trước đó xác nhận 99.003 khối còn thiếu. Bắt đầu ghi theo mẻ GPU 2; mã nguồn backend không đổi.
- Cập nhật lần cuối: 2026-09-27 15:53 +0700 (OMP — sao lưu mới đã xác minh; bắt đầu tiếp tục chỉ mục bằng GPU)
