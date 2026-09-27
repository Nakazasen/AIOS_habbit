# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `696c3ba` (Vé B: đang tiếp tục ghi vector bằng GPU theo mẻ 2)
- Báo cáo: `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 16:14 +0700 (máy h410asrock) — 2432/99003 khối còn thiếu đã được ghi bằng GPU, mẻ 2; bản sao lưu mới đã integrity_check=ok. Đang tiếp tục ghi vector bằng gpu theo mẻ 2.
- Cập nhật lần cuối: 2026-09-27 16:14 +0700 (OMP — đang tiếp tục ghi vector bằng GPU theo mẻ 2)
