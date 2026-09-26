# FIX 2 migration ONNX — Bước A: script + test + dry-run (chờ duyệt apply)

Ngày: 2026-09-26. Hostname: `h410asrock`. Branch: `phieu-viec/rag-fix1`.
Ticket: `docs/phieu-viec/mailbox/prompt.md` (Bước A only). Không đụng `main`.
Không ghi index trong Bước A (dry-run chỉ đọc).

## Kết luận trước

- Script mới `scripts/migrate_vectors_to_onnx.py`: mặc định dry-run, chỉ ghi
  khi có `--apply` **và** `BGE_BACKEND=onnx` (hoặc `onnx_int8`) đặt tường minh
  **và** tồn tại backup sibling `library.sqlite.bak-*` verify `ok`.
  Runtime mặc định vẫn PyTorch; không đổi logic fingerprint.
- Dry-run trên index thật: **340 pending / 340 retrievable, 0 đã migrate**,
  fingerprint cũ (PyTorch) `ce7fb53f797f…`, mới (ONNX fp32) `016c5255d0ce…`.
  Index 9.764.864 byte. Ước tính cold ~2,15 giờ (22,8 s/chunk × 340),
  warm ~10,2 phút (1,8 s/chunk × 340).
- Unit test mới `tests/test_rag_v2_migrate_onnx.py`: 4 passed (pending-count,
  dry-run không ghi checksum/size, gate flag, gate backup, apply + resume).
- DỪNG ở Bước A theo ticket: chưa backup mới, chưa `--apply`. Chờ duyệt số
  liệu 340 pending + ước tính trên trước khi sang Bước B.

## 1. Script migration

- `plan_migration(index)`: mở backend ONNX pinned, lấy fingerprint hiện tại,
  liệt kê chunk retrievable thiếu dense row cùng fingerprint (so content hash
  bằng Python vì hàm hash nằm ngoài sqlite), đồng thời đọc fingerprint cũ duy
  nhất còn lại trong `chunk_embeddings` (PyTorch `ce7fb53f…`; rỗng nếu có
  nhiều/không có fingerprint cũ — không trộn fingerprint). Chỉ đọc (`mode=ro`).
- `apply_migration(index, plan, batch_size=10)`: từ chối khi
  `BGE_BACKEND` không phải onnx/onnx_int8; từ chối khi thiếu backup sibling
  `library.sqlite.bak-*` hoặc backup `integrity_check` không `ok`; kiểm tra
  fingerprint của plan khớp backend đang pinned; mỗi batch commit độc lập
  dense + sparse (`ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE`), in
  progress từng batch; resume bằng cách bỏ qua chunk đã mang fingerprint ONNX.
- Không đụng vector fingerprint khác (340 vector PyTorch giữ nguyên); không
  đụng `chunks`, schema, hay text.
- CLI: `migrate_vectors_to_onnx.py INDEX [--apply] [--batch-size N] [--json]`.

## 2. Test

`tests/test_rag_v2_migrate_onnx.py` (dùng `DeterministicEmbeddingBackend` cho
index tạm + fake backend ONNX, không cần model 2,2 GB):

- `test_plan_counts_pending_without_writing`: plan ra 2 pending + fingerprint
  cũ, sha256/size file không đổi.
- `test_apply_requires_explicit_onnx_flag`: thiếu `BGE_BACKEND` → `SystemExit`.
- `test_apply_requires_sibling_backup`: có flag nhưng thiếu backup → `SystemExit`.
- `test_apply_migrates_and_resumes`: apply batch-size 1 migrate 2 chunk, plan
  lại ra 0 pending, apply lại trả 0, đủ 2 dense + 2 sparse fingerprint mới,
  tổng dense 4 (giữ 2 cũ).

Kết quả: `pytest tests/test_rag_v2_migrate_onnx.py -q` → **4 passed**.

## 3. Dry-run index thật (chỉ đọc)

Lệnh:

```
BGE_BACKEND=onnx PYTHONPATH=D:/Sandbox/AIOS_habbit/src \
.venv/Scripts/python.exe scripts/migrate_vectors_to_onnx.py \
local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --json
```

Kết quả:

```json
{
  "index_bytes": 9764864,
  "retrievable_chunks": 340,
  "already_onnx": 0,
  "pending_chunks": 340,
  "onnx_fingerprint": "016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb",
  "pytorch_fingerprint": "ce7fb53f797f0973e2cbf51d6a6ffef4de9a32b659b979f45663c6c360c8e43c",
  "estimate_cold_s": 7752.0,
  "estimate_warm_s": 612.0
}
```

- `dry_run: no changes written`; mtime index giữ 2026-09-26 09:13,
  `integrity_check` → `ok` sau dry-run.
- Số 340 pending khớp chẩn đoán commit `1488e77` (340 vector PyTorch
  `ce7fb53f…` đều thiếu fingerprint ONNX `016c5255…`).
- Ước tính dựa trên số đo thực tế máy này: chunk đầu cold 22,8 s, warm
  1,6–1,8 s/chunk (bench vòng 3: 1631 ms/doc). Thực tế `--apply` sẽ nằm giữa
  hai mốc: batch đầu chậm, các batch sau ấm dần; cần giám sát và dừng nếu quá
  chậm gấp 2 lần ước tính warm theo phiếu.

## 4. Phạm vi Bước B (chưa làm, chờ duyệt)

1. Backup mới `library.sqlite.bak-<YYYYMMDD-HHMM>` + verify `ok`.
2. `BGE_BACKEND=onnx ... migrate_vectors_to_onnx.py INDEX --apply`
   (batch 10, commit từng batch, resume tự nhiên).
3. Verify: vector fingerprint `016c5255…` = 340; `integrity_check ok`.
4. Báo cáo `FIX2_migrate-onnx-apply.md`, commit riêng, push, dừng.

Files commit Bước A: `scripts/migrate_vectors_to_onnx.py`,
`tests/test_rag_v2_migrate_onnx.py`, báo cáo này. Không merge `main`.
