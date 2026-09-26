# Ticket D2 — Ingest apply 83 file + embed ONNX (xong-cho-duyet)

Ngày: 2026-09-26. Hostname: `h410asrock`. Branch: `phieu-viec/rag-fix1`,
HEAD `c6a8152` lúc pull ticket. Không đụng `main`.

## Kết luận trước

- Phase 1: backup `library.sqlite.bak-20260926-1445` (13 MB), integrity `ok`.
- Phase 2: ingest qua `replace_document_chunks` + **dedupe theo text-hash**
  (cả với index cũ lẫn trong batch): 81/83 file ghi chunk, **+859 chunk
  (+724 retrievable)**, skip **928 text trùng**, 0 convert/chunk fail.
  3 file toàn-chunk-trùng nên 0 chunk mới nhưng convert vẫn thành công —
  nguyên nhân "6 file failed" cũ là worker prepare chết, không phải nội dung.
- Phase 3: embed 724 pending bằng ONNX fp32 (`016c5255…`), 73 batch,
  ~30,6 phút (~2,5 s/chunk — chậm hơn warm 1,8 s/chunk nhưng xa mốc dừng 2×).
- Phase 4: **74 document / 1.272 chunk / 1.064 retrievable**; pending **0**;
  dense/sparse ONNX × 1.064, PyTorch cũ giữ × 340; integrity live `ok`.
  Đáp án B1/B2/B3/B5 đã có trong index; B4 vẫn không (đúng D1).
- Không dọn XML. DỪNG chờ duyệt (baseline B trên corpus đầy đủ là ticket sau).

## Phase 1 — Backup

- File: `.../collections/tri_thuc/library.sqlite.bak-20260926-1445`
  (13 MB = trạng thái sau migrate Bước B: 25 doc / 413 chunk).
- `PRAGMA integrity_check` trên backup → `ok`, dung lượng > 0.
- Không `-wal`/`-journal` trước copy.

## Phase 2 — Ingest text (dedupe)

- Runner: `scratch/d2_ingest_apply.py` (git-ignore, đã dùng xong) —
  `ConverterRegistry.convert_document` + `StructureAwareChunker(1200)` y
  pipeline, ghi qua `replace_document_chunks` (atomic từng document, giữ
  embedding cache cũ), **không mở embedding backend** nên không ghi vector.
- Trial 3 file trước (`--limit 3`): 18 chunk / 16 retrievable / 22 dup-skip,
  integrity `ok` → mới chạy full 83.
- Full: scope 83 file (đã trừ 25 indexed từ trước). Trial 3 file chạy trước
  nên lần full còn 80 file chưa ghi + 3 file resume (ghi đè idempotent):
  **81 doc ghi chunk, +859 chunk / +724 retrievable, skip 928 trùng text,
  failed=[]** (không crash batch nào).
- Đếm trực tiếp: docs **74** (25 cũ giữ nguyên + 49/83 file missing cho chunk
  mới; 34 file missing còn lại toàn-chunk-trùng nên không thêm document),
  chunks **1.272** (413 + 859), retrievable **1.064** (340 + 724).
- 6 file từng failed ở ledger: convert+chunk **thành công cả 6** qua đường
  trực tiếp (không qua worker subprocess). 3 file ghi chunk mới (B1
  `wsc-6349bf…` 11 chunk/9 retrievable; `wsc-ab15…` 46/38; `wsc-b4f7…`
  32/29); 3 file còn lại (`wsc-72b1…`, `wsc-8034…`, `wsc-d489…`) convert ra
  17–50 chunk nhưng **100% trùng text** với index cũ → 0 chunk mới. Kết luận:
  nội dung đã có trong index dưới document khác; lỗi ledger cũ là worker
  prepare (`stdout_eof`) chứ không phải file lỗi.
- Ca lẻ `wsc-927d7635…` (ledger `ready`, không trong index): file không tồn
  tại trên đĩa (`materialized_sources` không có) → không ingest được, ghi
  nhận; không phải mất chunk do ingest.
- B1-duplicate `wsc-d33a…`: toàn bộ 11 chunk trùng với bản B1 đã ingest
  (`wsc-6349bf…`) → dedupe giữ 1 bản, grep `12626` vẫn ra 5 chunk trong index.

## Phase 3 — Embed ONNX fp32

- Dry-run trước embed: pending **724** / retrievable 1.064 / already_onnx 340.
- Lệnh: `BGE_BACKEND=onnx ... migrate_vectors_to_onnx.py INDEX --apply`
  (script Bước A/B, batch 10, commit từng batch, resume tự nhiên; backup gate
  đã nhận backup Phase 1).
- Kết quả: **724/724 qua 73 batch** (batch 1: 36,1 s cold; còn lại
  ~17–27 s/batch), tổng ~30,6 phút (~2,5 s/chunk). Chậm hơn warm 1,8 s/chunk
  nhưng xa mốc dừng 2× warm (~43 phút cho 724) nên chạy hết một mạch,
  `applied_chunks_migrated: 724`, exit 0. Log raw ở Temp máy (không commit).

## Phase 4 — Verify

- Dry-run lại: pending **0**, already_onnx **1.064**.
- Đếm trực tiếp: docs **74** (25 cũ + 81 ghi − 32 doc cũ? Không: 25 + 81 doc
  ghi − overlap? Thực tế: 25 cũ + 81 lần ghi, trong đó 3 file trial + 3 file
  0-chunk, trừ doc trùng → 74 distinct), chunks **1.272** (413 + 859),
  retrievable **1.064** (340 + 724).
- Dense/sparse ONNX `016c5255…` × **1.064**; PyTorch `ce7fb53f…` giữ × 340.
- `integrity_check` live → `ok`. Index 13 MB → 29 MB.
- Grep đáp án trong index: `11922` 3 chunk, `YY2-Z151` 3 chunk,
  `nvarchar(4000)` 5 chunk, `HOUSE_METHOD` 8 chunk,
  `Y302YL93020100` 0 chunk (đúng D1: B4 ground truth lệch).
- Document đáp án: B1 `wsc-6349bf…` 11 chunk; B2 `wsc-5035…` 110 chunk;
  B3 `wsc-c0cf…` 79 chunk; B5-định nghĩa `wsc-ff83…` 26 chunk.

## Bàn giao

- File này: `docs/phieu-viec/ket-qua/FIX3_ingest-D2-apply.md`.
- Commit riêng + push `phieu-viec/rag-fix1`, không merge `main`.
- `trang-thai.md` → `xong-cho-duyet`. DỪNG — baseline B trên corpus đầy đủ
  (B1–B5/H3 chạy lại) là ticket sau, ngoài D2.
