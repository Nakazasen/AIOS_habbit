# Nghiệm thu FIX 3 lần 3 — backfill 12/24 trên máy nhà + chạy đủ 13 câu (KHÔNG ĐẠT đúng/sai B)

Ngày: 2026-09-26
Nhánh: `phieu-viec/rag-fix1` (không đụng `main`)
Không sửa code trong vòng này (chỉ thêm script chạy nghiệm thu ở `scratch/`,
thư mục này git-ignore nên không vào commit).

## Kết luận trước

- Đã `--apply` theo đúng phạm vi duyệt: máy `h410asrock`, index canary
  9.588.736 byte, đúng 12 summary / 24 trường, trên backup
  `library.sqlite.bak-20260926-0842` đã verify `ok`.
- Sau apply: **12/12 summary có fingerprint, 12/12 có privacy**
  (`["cloud_safe"]`), `integrity_check` → `ok`. Khớp điều kiện duyệt.
- Chạy đủ 13 câu với cả hai flag
  (`AIOS_RAG_V2_SUMMARY_FIRST=1`, `AIOS_RAG_V2_SUMMARY_PROVENANCE=1`):
  A1–A5 + H1–H2 vào `overview`/`summary_only`, không abstain, có dòng
  `Ghi chú: trả lời ở mức tổng quan.`; B1–B5 + H3 đi `hybrid`, không abstain.
  Nhưng đối chiếu đáp án tham chiếu: **B1–B5 đều không chứa đáp án đúng**,
  nên vòng này KHÔNG ĐẠT về đúng/sai chi tiết.
- Lỗi nền đã biết A3/A5 (khung PRECHECKS/STEPS/POSTCHECKS rỗng nhưng
  abstained=false, tồn tại cả khi tắt flag) vẫn còn, không tính vào vòng này.
- Phạm vi duyệt chỉ bao máy nhà. Index máy công ty vẫn chưa `--apply`; muốn
  nghiệm thu ở máy công ty phải làm một vòng riêng với số 10/20/0 ở đó.

## Bước 0 — Máy và index

- Hostname: `h410asrock` (máy nhà, không phải máy công ty `KDTVN-PC0575`).
- Branch: `phieu-viec/rag-fix1`, tree sạch trước khi chạy.
- Index (canary theo đúng yêu cầu):
  `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  (9.588.736 byte lúc backup, mtime 2026-09-11 06:39; sau apply 9.764.864 byte,
  mtime 2026-09-26 09:13 — tăng do điền 24 trường, đúng dự kiến).
- Ghi chú: còn một index production khác lớn hơn trên máy này
  (`local_runs/workspace_chat_rag_v2_production/.../tri_thuc/library.sqlite`,
  28.753.920 byte, mtime 2026-09-13 21:16), nhưng vòng này chỉ chạy đúng đường
  canary như phiếu yêu cầu.

## Bước 1 — Backup

- Đã copy `library.sqlite` thành
  `library.sqlite.bak-20260926-0842` (9.588.736 byte) trước mọi thao tác ghi.
- Verify backup: mở bằng sqlite3 read-only, `PRAGMA integrity_check` → `ok`,
  `count(document_summary)` = 12, số summary có fingerprint = 0 (đúng trạng
  thái trước apply).
- File `.bak-*` đã nằm trong diện git-ignore nên không lọt vào commit.

## Bước 2 — Write lock

- Không có `library.sqlite-wal`, không có `library.sqlite-journal`.
- File `.aios-library-writer.lock` chỉ 1 byte, mtime 2026-09-08 00:15 (cũ, từ
  lúc ingest, không phải lock đang giữ).
- Mở kết nối sqlite read-only thành công, `integrity_check` → `ok`.
- Lần đầu verify sau apply bị timeout do máy đang chạy tiến trình
  `graphify.exe update` nặng (~1,8 GB RAM); các lần đọc nhỏ lẻ sau đó đều OK,
  không có dấu hiệu kẹt lock.

## Bước 3 — Dry-run trước apply (bật AIOS_RAG_V2_SUMMARY_PROVENANCE=1)

Lệnh (PYTHONPATH trỏ `src` vì venv không cài package ở chế độ editable):

```
PYTHONPATH=D:/Sandbox/AIOS_habbit/src AIOS_RAG_V2_SUMMARY_PROVENANCE=1 \
D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe \
scripts/backfill_summary_provenance.py \
local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --json
```

Kết quả (chạy lại ngay trước apply, khớp dry-run vòng trước):

- `summary_count`: **12** (bàn giao FIX 5 máy công ty: 10 — lệch đã được duyệt)
- `update_count`: **24** = 12 fingerprint + 12 privacy (bàn giao: 20)
- `skipped_ambiguous_count`: **0**, `skipped_no_body_value_count`: **0**
- 12 fingerprint đề xuất trùng fingerprint chunk thân cùng document 100%;
  privacy đề xuất đều `["cloud_safe"]`.
- `chunks` theo `file_type`: `txt` 401, `document_summary` 12; 25 document_id
  khác nhau (12 document có summary + body, 13 document chỉ có body).
- Không ghi gì (`dry_run: no changes written`).

## Bước 4 — Apply (đã duyệt) + verify

Lệnh: cùng lệnh dry-run thêm `--apply`. Output:
`summary_count 12, update_count 24, skipped_ambiguous 0, skipped_no_body 0`,
`applied_rows_changed: 24`.

Verify sau apply (chỉ đọc):

- Tổng summary: 12; có fingerprint (non-null/non-empty): **12**;
  có privacy (non-null/non-`[]`): **12**; giá trị privacy duy nhất
  `["cloud_safe"]`.
- Mở mẫu 3 summary đầu (`wsc-50e045…`, `wsc-54179f…`, `wsc-624b70…`): fingerprint
  12 ký tự đầu khớp fingerprint chunk thân cùng document, privacy
  `["cloud_safe"]`, không null/rỗng.
- `PRAGMA integrity_check` trên index sau apply → `ok`.
- Đối chiếu backup: backup vẫn 12 summary / 0 fingerprint (nguyên trạng trước
  apply); index live 12/12 (đúng phần việc đã duyệt).

## Bước 5 — Nghiệm thu FIX 3 (cả hai flag bật)

Cách chạy: script `scratch/fix3_acceptance_lan3.py` (git-ignore, không commit),
config `RagV2DevConfig` read-only trỏ thẳng index canary thật, profile
`bge_m3_hybrid`, model BGE-M3 local
(`bge-m3-5617a9f`, rev `5617a9f…`, checksum `sha256:b1d887…`), worker
subprocess PyTorch/FlagEmbedding 1.3.5 trên CPU. Specs = 25 file
`materialized_sources/wsc-*.txt` có mặt trong index (privacy `cloud_safe`,
`owner_consent=True`) — đúng cơ chế chọn nguồn của pipeline (lần chạy đầu để
specs rỗng nên toàn bộ B abstain `source_filter_excluded_all_chunks`; đã sửa
và chạy lại, đó là lỗi dàn dựng của agent, không phải lỗi sản phẩm).
Init worker (không tính vào giây từng câu): 97,18 giây.

Kết quả từng câu (mode = `synthesis.mode`, path = `routing.effective_path`):

| Câu | Giây | Abstain | Mode | Path | Ghi chú tổng quan | Đáp án tham chiếu |
| --- | ---: | --- | --- | --- | --- | --- |
| A1 | 0,64 | không | local_extractive_provider_fallback | summary_only | có | — (tổng quan, không chấm) |
| A2 | 0,20 | không | local_extractive_provider_fallback | summary_only | có | — |
| A3 | 0,11 | không | local_citation_first_provider_fallback | summary_only | có | — (lỗi nền đã biết: khung rỗng) |
| A4 | 0,14 | không | local_extractive_provider_fallback | summary_only | có | — |
| A5 | 0,12 | không | local_citation_first_provider_fallback | summary_only | có | — (lỗi nền đã biết: khung rỗng) |
| B1 | 101,61 | không | local_extractive_provider_fallback | hybrid | không | SAI: không có 11922/12860/12626 |
| B2 | 2,25 | không | local_extractive_provider_fallback | hybrid | không | SAI: không có YY2-Z151.exe/YY2-Z152.exe |
| B3 | 3,64 | không | local_extractive_provider_fallback | hybrid | không | SAI: không có nvarchar(4000)/4000; lẫn XML `xmlns` slide |
| B4 | 2,19 | không | local_extractive_provider_fallback | hybrid | không | SAI: không có 14 ký tự/Y3/Y302YL93020100 |
| B5 | 1,81 | không | local_extractive_provider_fallback | hybrid | không | SAI: không có HOUSE_METHOD '0'/'1' |
| H1 | 0,05 | không | local_extractive_provider_fallback | summary_only | có | — (held-out tổng quan, có trả lời) |
| H2 | 0,04 | không | local_extractive_provider_fallback | summary_only | có | — (held-out tổng quan, có trả lời) |
| H3 | 1,18 | không | local_extractive_provider_fallback | hybrid | không | — (held-out, `hybrid` như FIX 5: câu có chữ "trình tự") |

Nhận xét:

- A1/A2/A4/H1: trả lời từ summary, có citations [1]–[5] và dòng tổng quan.
  A3/A5: vẫn khung PRECHECKS/STEPS/POSTCHECKS rỗng + `LIMITATIONS:
  provider_synthesis_unavailable` + dòng tổng quan — đúng lỗi nền đã biết,
  tồn tại cả khi tắt flag, không tính vào vòng này.
- H2 vào `overview`/`summary_only` (lần này), khác FIX 5 trên bản copy máy
  công ty cũng `summary_only` — nhất quán.
- B1–B5: không abstain (tiến bộ so với abstain toàn bộ khi specs rỗng), nhưng
  toàn văn là các chunk chung chung (MOM Control PLC, ERD, slide XML), không
  chứa bất kỳ đáp án tham chiếu nào. Limitations chung:
  `incomplete_query_term_coverage` (+ `provider_network_error` do synthesis
  provider không gọi được mạng, đã fallback extractive).
- B3 lẫn XML `xmlns` slide (`<p:sld xmlns:a=... xmlns:r=... xmlns:p=...>`) —
  summary/chunk thân đang lẫn nội dung thô slide, đúng vấn đề FIX 3 đã nêu
  (chất lượng trích xuất bị kéo bởi XML).
- Không câu nào timeout (timeout query 180 giây). `BGE_BACKEND` không đổi
  (mặc định `pytorch`).

## Bước 6 — Commit + push

- File báo cáo này: `docs/phieu-viec/ket-qua/FIX3_nghiem-thu-lan3.md`
  (ghi đè bản "dừng ở dry-run" đã push ở commit `d130bfc`).
- Commit riêng + push `phieu-viec/rag-fix1`, không merge `main`.
- Raw JSONL 13 câu + toàn văn A/H/B lưu ở
  `C:/Users/Admin/AppData/Local/Temp/fix3_lan3c_answers.jsonl`,
  `fix3_AH_full.txt`, `fix3_B_full.txt` trên máy `h410asrock` (không commit).
- Sau push DỪNG, chờ duyệt hướng xử lý B sai toàn bộ (nghi ngờ corpus máy nhà
  thiếu/giấu chi tiết có mã, hoặc retrieval chưa tới chunk chứa đáp án —
  cần điều tra riêng, ngoài phạm vi phiếu này).
