# FIX 2 migration ONNX — Bước B: backup mới + --apply 340 chunk (chờ duyệt Bước C)

Ngày: 2026-09-26. Hostname: `h410asrock`. Branch: `phieu-viec/rag-fix1`.
Ticket: `docs/phieu-viec/mailbox/prompt.md` (Bước B only, đã duyệt apply).
Không đụng `main`. Không đổi fingerprint semantics, runtime mặc định vẫn PyTorch.

## Kết luận trước

- Backup mới `library.sqlite.bak-20260926-1142` (9.764.864 byte),
  `integrity_check` → `ok` trước mọi lần ghi.
- `--apply` với `BGE_BACKEND=onnx`: **migrate 340/340 chunk qua 34 batch**,
  tổng ~11,6 phút (693,5 s, ~2,04 s/chunk — trong ngưỡng warm, không chạm mốc
  dừng 2× warm ~20 phút).
- Verify: dry-run lại pending **0**; dense ONNX `016c5255…` = **340**,
  dense PyTorch `ce7fb53f…` = **340** (giữ nguyên, không ghi đè); sparse hai
  fingerprint đều 340; `integrity_check` live → `ok`.
- Dọn kèm 2 nit review Bước A trong cùng commit script: xóa hằng chết
  `BGE_M3_MODEL_PATH`/`BGE_M3_CHECKSUM`, thêm comment giải thích tên nội bộ
  legacy `onnx_int8`.
- DỪNG ở Bước B: chưa chạy worker ONNX (Bước C, ticket riêng).

## B1. Backup

- File: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite.bak-20260926-1142`
  (9.764.864 byte, copy lúc 11:42 giờ máy local, trước apply).
- Verify: `PRAGMA integrity_check` trên backup → `ok`; dense trên backup chỉ
  có PyTorch `ce7fb53f…` × 340 (đúng trạng thái trước apply).
- Script tự kiểm tra backup sibling mới nhất + integrity trước khi ghi
  (`_require_fresh_backup`); lần apply này đã in
  `backup: library.sqlite.bak-20260926-1142 (integrity ok)`.

## B2. Apply

Lệnh đúng ticket:

```
BGE_BACKEND=onnx PYTHONPATH=D:/Sandbox/AIOS_habbit/src \
.venv/Scripts/python.exe scripts/migrate_vectors_to_onnx.py \
local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --apply
```

- Plan đầu: retrievable 340, already_onnx 0, pending 340,
  ONNX `016c5255…`, PyTorch `ce7fb53f…`.
- Batch 10 chunk, commit từng batch, progress đầy đủ (log raw ở
  `C:/Users/Admin/AppData/Local/Temp/fix2_migrate_apply.log` trên máy
  `h410asrock`, không commit). Từng batch 16,9–24,5 s (~1,7–2,5 s/chunk);
  tổng 693,5 s ≈ 11,6 phút — nhỉnh hơn ước tính warm 10,2 phút nhưng xa mốc
  dừng 2× warm (~20 phút) nên chạy tiếp đến hết, không resume giữa chừng.
- Kết quả: `applied_chunks_migrated: 340`, exit 0. Index live tăng
  9.764.864 → ~13 MB (thêm 340 dense + 340 sparse row ONNX).

## B3. Verify

- Dry-run lại (không `--apply`): pending **0**, already_onnx **340**,
  retrievable 340, `dry_run: no changes written`.
- Đếm trực tiếp: dense ONNX `016c5255…` = 340, dense PyTorch `ce7fb53f…` =
  340; sparse ONNX = 340, sparse PyTorch = 340; retrievable chunks = 340.
- `PRAGMA integrity_check` trên index live → `ok`.
- Đối chiếu backup: backup vẫn dense PyTorch × 340, không có row ONNX
  (nguyên trạng trước apply).

## B4. Phạm vi Bước C (chưa làm, chờ ticket riêng)

1. Chạy worker `BGE_BACKEND=onnx` trên index đã migrate: ghi init
   (kỳ vọng < 300 s; cold ~62 s + warm).
2. Chạy lại B1–B5 (hai flag summary như nghiệm thu lần 3), đối chiếu latency
   và đáp án với bản PyTorch (B1 101,61 s / B2 2,25 s / B3 3,64 s /
   B4 2,19 s / B5 1,81 s).

Files commit Bước B: `scripts/migrate_vectors_to_onnx.py` (2 nit),
báo cáo này. Không merge `main`.
