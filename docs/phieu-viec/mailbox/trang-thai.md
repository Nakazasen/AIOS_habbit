# Trạng thái mailbox

- Trạng thái: `dang-lam`
- Ticket hiện tại: Vé A — chốt điểm dừng G1 (verify integrity index ~1,7GB + ghi điểm resume chính xác, chỉ đọc) → Vé B — đường GPU (khảo sát onnxruntime-gpu + CUDA cho GTX 1060 3GB, mẻ thử 20 chunk; đạt thì resume pending bằng GPU, không đạt thì báo chạy CPU tiếp)
- Ticket trước: G1 — TẠM DỪNG theo lệnh user 2026-09-27 (đã dừng mẻ embed CPU; file index ~1,7GB nguyên vẹn; nạp văn bản 433/433 xong, embedding chạy dở giữa chừng)
- Commit: `d2db518` (OMP mốc quick_check + dry-run)
- Báo cáo: đang viết `docs/phieu-viec/ket-qua/G1_checkpoint_diem-dung.md`
- Ghi chú: 2026-09-27 14:11 +0700 (máy h410asrock) — `integrity_check=ok`; size trước/sau 1.698.164.736 byte. Resume: chunk đầu pending `1172f198bf3cc27b159ec9ece90d02d9e420bb37cf96f732a93401386e1c2bf6`, doc `wsc-9c82b1ca2e1898a8d9d03e8b`, batch 1/9.901 (pending list sắp theo `chunk_id`, batch size 10); 99.003 pending.
- Cập nhật lần cuối: 2026-09-27 14:11 +0700 (OMP — mốc integrity + resume)
