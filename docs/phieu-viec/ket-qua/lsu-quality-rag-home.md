# Vé LSU-QUALITY-RAG-HOME — DỪNG vì md5 index lệch (báo ngay theo ticket)

- Vé: `LSU-QUALITY-RAG-HOME` (prompt `docs/phieu-viec/mailbox/prompt.md`).
- Máy: nhà `h410asrock`, user `Vinh`. Thời gian: 2026-10-07 ~00:40 +07.
- Trạng thái: **DỪNG trước khi đo** — đúng điều kiện ticket: md5 lệch thì dừng, báo ngay.
- Không sửa code, không ghi index, không merge `main`.

## 1. Điều kiện ticket áp dụng

Ticket khóa: ghi SHA256/md5 index máy nhà để đối chiếu với index PC0575
(md5 giữa chừng PC0575: `a7c7c2325949c05d3396ab5371e42e64` — lệch thì DỪNG, báo ngay).

## 2. Số đo index máy nhà (chỉ đọc)

- Đường dùng: `C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  (index production của máy nhà; file `local_runs/.../production/...` trên máy này hiện là bản TẠM `062ec090`, md5 `7392ef9a...`, nên không dùng).
- Byte: `2.942.201.856`. mtime: `2026-10-01 08:27:27 +07` (nguyên trạng, không ai ghi).
- md5: `239009676829484049738866329de9f2`.
- SHA-256: `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0`
  (khớp ghim gốc các vé `merge-home`, `hodap-home`, `scan-o-d`, `index-split-home`).
- Đếm chỉ đọc: `chunks` 149.800 / `chunk_embeddings` 121.671 / `chunks_fts` 121.331 / `retrievable=1` 121.331.

## 3. Đối chiếu với PC0575

| Mục | Máy nhà (C:/...) | PC0575 (báo cáo `restore-index-split-pc0575.md`) |
|---|---|---|
| Byte | 2.942.201.856 | 2.853.646.336 (file hợp sau merge) |
| md5 | `239009676829484049738866329de9f2` | `a7c7c2325949c05d3396ab5371e42e64` |
| chunk / emb / FTS | 149.800 / 121.671 / 121.331 | 149.800 / 121.671 / 121.331 |

Nội dung logic khớp 100% (cùng 149.800 chunk, cùng 121.671 vector, cùng 121.331 FTS;
khối tách của PC0575 vốn tách từ đúng file này — manifest ghi nguồn
`C:\AIOS_workspace_chat_rag_v2_production\...\library.sqlite` size 2.942.201.856).
Chỉ md5 cấp file lệch — do PC0575 hợp lại 4 khối thành file mới (layout trang SQLite khác),
không phải lệch nội dung.

## 4. Kết luận và đề nghị

- **Kết luận: DỪNG, chưa đo câu nào** (0/50), đúng ticket. Không có điểm số nào để báo.
- Đề nghị Muse/user chọn một trong hai rồi OMP chạy tiếp:
  1. Chấp nhận index nhà hiện hành (nội dung khớp, SHA-256 gốc khớp) và cho đo tiếp 50 câu CPU-only;
  2. Hoặc yêu cầu đồng bộ md5 cấp file trước (vacuum/hợp lại cho khớp byte) rồi đo.
- Ghi nhận sẵn cho bước đo (không chặn quyết trên):
  CPU-only đủ bằng chứng (mã `bge_onnx_backend.py` ghim `providers=["CPUExecutionProvider"]`,
  `device="cpu"`; `onnxruntime` máy chỉ có `CPUExecutionProvider`;
  `CUDA_VISIBLE_DEVICES=""`, `AIOS_RETRIEVAL_DEVICE=cpu`).
  Cầu nối tổng hợp `127.0.0.1:8585` hiện TẮT (`unavailable`) — khi cho đo tiếp cần dựng sidecar Antigravity `direct_ready` như vé digest.
