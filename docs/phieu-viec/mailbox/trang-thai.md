# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Vé P1.2 — Xác định kho production thật của collection tri_thuc (chỉ đọc)
- `commit`: ``
- `bao_cao`: ``
- `ghi_chu`: 2026-09-28 05:26 +07 (Muse) — Vé P1.1 verdict CHƯA ĐẠT đóng dấu (không phải lỗi OMP: dừng fail-closed đúng vé khi storage_root rỗng). Muse đã tra code độc lập: storage_root rỗng → `<runtime_root>/<profile>/collections/tri_thuc/library.sqlite` (code + test `test_default_collection_uses_dedicated_folder` xác nhận). Vé P1.2 cho chuỗi phân giải chính xác (repo root → manifest/env → runtime_root/profile). Bước 1 của P1 đã đạt, không làm lại.
- Ticket trước: Vé P1.1 — CHƯA ĐẠT đóng dấu 2026-09-28 ~05:18: storage_root rỗng, dừng fail-closed, không bịa đường dẫn; báo cáo `docs/phieu-viec/ket-qua/VE_P1_1_dong-dau-kho-that.md` (commit `bdda73c`).
- Ticket trước nữa: Vé P1 — CHƯA ĐẠT đóng dấu 2026-09-28 ~05:10: bước 1 đạt (integrity ok, 107331/107331 ONNX, fingerprint khớp, pending=0); bước 2–5 chưa chạy vì vé ghi sai đường dẫn production; báo cáo `docs/phieu-viec/ket-qua/VE_P1_dong-dau-kho-that.md` (commit `4ec8567`).
