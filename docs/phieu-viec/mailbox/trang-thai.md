# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `d4c292b` (OMP nhận vé A)
- Báo cáo: chưa có (vé A đang làm)
- Ghi chú: 2026-09-27 13:49 +0700 (máy h410asrock) — đã đếm nhanh chỉ-đọc: 133.144 chunk / 107.331 truy xuất được / 496 doc; dense ONNX `016c5255…` 8.328, PyTorch `ce7fb53f…` 340, pending naive 99.003 (chưa tính content_hash đổi text; integrity_check đang chạy riêng, file ~1,7GB nên chậm).
- Cập nhật lần cuối: 2026-09-27 13:49 +0700 (OMP — mốc đếm fingerprint)
