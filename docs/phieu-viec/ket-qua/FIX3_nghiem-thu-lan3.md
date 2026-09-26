# Nghiệm thu FIX 3 lần 3 — DỪNG ở dry-run: máy nhà lệch số bàn giao FIX 5

Ngày: 2026-09-26
Nhánh: `phieu-viec/rag-fix1` (không đụng `main`)
Không sửa code trong vòng này.

## Kết luận trước

**DỪNG, chưa `--apply`, chưa chạy nghiệm thu A1–A5/B1–B5/H1–H3.**
Lý do: dry-run trên máy này không khớp bàn giao FIX 5 (10/20/0/0), mà phiếu
yêu cầu đúng trường hợp này phải dừng xin duyệt.

## Bước 0 — Máy và index

- Hostname: `h410asrock` (máy nhà, không phải máy công ty `KDTVN-PC0575`).
- Branch: `phieu-viec/rag-fix1`, tree sạch (`git status --short` không có gì).
- Index đã kiểm tra (canary theo đúng yêu cầu):
  `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  (9.588.736 byte, mtime 2026-09-11 06:39).
- Ghi chú: còn một index production khác lớn hơn tồn tại trên máy này
  (`local_runs/workspace_chat_rag_v2_production/.../tri_thuc/library.sqlite`,
  28.753.920 byte, mtime 2026-09-13 21:16), nhưng vòng này chỉ chạy đúng đường
  canary như phiếu yêu cầu.

## Bước 1 — Backup

- Đã copy `library.sqlite` thành
  `library.sqlite.bak-20260926-0842` (9.588.736 byte).
- Verify backup: mở bằng sqlite3 read-only, `PRAGMA integrity_check` → `ok`,
  `count(document_summary)` trên backup = 12.
- File `.bak-*` đã nằm trong diện git-ignore nên không lọt vào commit.

## Bước 2 — Write lock

- Không có `library.sqlite-wal`, không có `library.sqlite-journal`.
- File `.aios-library-writer.lock` tồn tại nhưng chỉ 1 byte, mtime 2026-09-08
  00:15 (cũ, từ lúc ingest, không phải lock đang giữ).
- Mở kết nối sqlite read-only thành công, `integrity_check` → `ok`.
- Đủ điều kiện đọc; nhưng theo bước 3 vẫn dừng, không apply.

## Bước 3 — Dry-run (bật AIOS_RAG_V2_SUMMARY_PROVENANCE=1, không --apply)

Lệnh (PYTHONPATH trỏ `src` vì venv không cài package ở chế độ editable):

```
PYTHONPATH=D:/Sandbox/AIOS_habbit/src AIOS_RAG_V2_SUMMARY_PROVENANCE=1 \
D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe \
scripts/backfill_summary_provenance.py \
local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --json
```

Kết quả:

- `summary_count`: **12** (bàn giao FIX 5: 10)
- `update_count`: **24** = 12 fingerprint + 12 privacy (bàn giao: 20)
- `skipped_ambiguous_count`: **0** (khớp)
- `skipped_no_body_value_count`: **0** (khớp)
- Không ghi gì (`dry_run: no changes written`).

Điều tra thêm, chỉ đọc:

- `chunks` theo `file_type`: `txt` 401, `document_summary` 12.
- Cả 12 summary đều thiếu fingerprint (null/rỗng) và thiếu privacy (`[]`).
- Mỗi summary đều có chunk thân cùng `document_id`: số chunk thân 5–128,
  mỗi document đúng 1 fingerprint và đúng 1 bộ privacy `["cloud_safe"]`.
- Toàn bộ 12 fingerprint dry-run đề xuất đều trùng fingerprint chunk thân cùng
  document; privacy đề xuất đều `["cloud_safe"]`.
- 12 text summary đều dài 1551 ký tự (tiền tố 1500 + overhead), cùng khuôn.
- Không có ca mơ hồ, không có ca thiếu giá trị ở chunk thân.

Nguyên nhân lệch số nhiều khả năng nhất: máy nhà ingest thêm 2 document so
với máy công ty lúc lập bàn giao (10 → 12). Đây là khác biệt dữ liệu giữa hai
máy, đúng điều FIX5_bao-cao.md mục 7 đã cảnh báo ("mỗi máy chạy độc lập").
Không phải lỗi logic backfill.

## Bước 4 — Apply: KHÔNG CHẠY

Phiếu yêu cầu: máy nhà không dùng 10/20/0 làm hằng số; chạy dry-run, ghi số
thực tế, rồi dừng xin duyệt, không tự ý `--apply`. Đã tuân thủ.

Để chạy tiếp khi được duyệt: dùng cùng lệnh trên thêm `--apply` với flag bật,
rồi đếm lại số summary đã có fingerprint + privacy (kỳ vọng 12/12 nếu duyệt
đúng index canary này), mở vài summary kiểm tra giá trị.

## Bước 5 — Nghiệm thu FIX 3: KHÔNG CHẠY

Vì chưa apply, 12 summary trên index canary máy nhà vẫn thiếu provenance nên
đường overview có flag vẫn sẽ abstain `no_document_summaries` như lần 2.
Chạy A1–A5/B1–B5/H1–H3 lúc này chỉ lặp lại kết quả cũ, không có giá trị nghiệm
thu, nên dừng theo phiếu.

Câu hỏi và đáp án tham chiếu giữ nguyên để dùng sau khi được duyệt apply:
B1 (thùng cũ ...11922, ...12860; thùng mới ...12626), B2 (ACR YY2-Z151.exe;
CTU YY2-Z152.exe), B3 (nvarchar(4000)), B4 (14 ký tự, đầu Y3, ví dụ
Y302YL93020100), B5 (HOUSE_METHOD '0' cất kho, '1' đưa kiểm tra).
Lỗi nền đã biết A3/A5 (khung PRECHECKS/STEPS/POSTCHECKS rỗng nhưng
abstained=false, tồn tại cả khi tắt flag) không tính vào vòng này.

## Bước 6 — Commit và chờ duyệt

- File báo cáo này: `docs/phieu-viec/ket-qua/FIX3_nghiem-thu-lan3.md`.
- Commit riêng + push `phieu-viec/rag-fix1`, không merge `main` (thực hiện sau
  khi viết xong báo cáo).
- Sau push DỪNG, chờ duyệt apply trên số liệu thực tế 12/24/0/0 của máy nhà.
