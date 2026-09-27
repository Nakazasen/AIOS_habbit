# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `342b0b8` (OMP mốc đếm fingerprint)
- Báo cáo: chưa có (vé A đang làm)
- Ghi chú: 2026-09-27 14:02 +0700 (máy h410asrock) — `quick_check=ok` (294,4s, chỉ-đọc); dry-run migrate ONNX: 107.331 truy xuất được / đã có ONNX 8.328 / pending 99.003 (khớp pending naive; ước warm ~2.970 phút). Đang chạy `integrity_check` đầy đủ + chốt batch resume.
- Cập nhật lần cuối: 2026-09-27 14:02 +0700 (OMP — mốc quick_check + dry-run)
