# Trạng thái mailbox

- Trạng thái: `moi`
- Ticket hiện tại: Vé KHẨN — Dừng P1.3; commit 3 fix retrieval + push ngay (lệnh user 06:51 +07)
- `prompt`: `docs/phieu-viec/mailbox/prompt.md`
- `ghi_chu`: 2026-09-28 ~12:05 +07 (Muse VM) — CẬP NHẬT VÉ KHẨN: user báo máy nhà TẮT từ 7h sáng (không phải "vé đang chạy"). Fix số 3 (safety_mode_label) đã được Muse implement + push trực tiếp: commit `491f53c` (2 test mới, 104 pass) để máy công ty không bị chặn B1–B5 trong hôm nay. OMP khi mở máy tối nay: BỎ local changes của `rag_v2_synthesis_provider.py` + test fix số 3, chỉ commit fix số 1 (`bge_subprocess_client.py`). Chi tiết trong prompt.md mục 2.
- Ticket trước: Vé P1.3 — DỪNG GIỮA CHỪNG theo lệnh user (đã xong backup + copy nguồn, SHA khớp; chưa chạy B1–B5); báo cáo `docs/phieu-viec/ket-qua/VE_P1_3_dong-dau-kho-that.md`.
