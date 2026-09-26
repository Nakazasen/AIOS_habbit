# Ticket D1 — Vì sao chỉ 25/108 document được index + dry-run ingest (chỉ đọc)

Ngày: 2026-09-26. Hostname: `h410asrock`. Branch: `phieu-viec/rag-fix1`,
commit `864832f` (ticket D1). Không đụng `main`.
Tuyệt đối chỉ đọc: sqlite mở `mode=ro`, không `--apply`, không ingest thật,
không sửa file index. Không dọn XML trong ticket này.

## Kết luận trước

- Index canary `tri_thuc` có **25 document / 413 chunk**; `materialized_sources`
  có **108 file**, **83 file không có path trong index** (đối chiếu 1–1,
  không có document_id lệch).
- Nguyên nhân 83 file, theo `source_preparation_ledger`
  (`workspace_chat.sqlite`, chỉ đọc):
  - **6 file đã thử ingest và failed** (`bge_worker_prepare_stdout_eof`;
    riêng B1 `wsc-6349bfab…` failed 34 lần) — trong đó có file đáp án B1/B5.
  - **77 file chưa bao giờ vào ledger** (không có dòng nào) — chưa từng được
    đưa vào pipeline.
  - Không có manifest/allowlist giới hạn 25 document; phân bố dung lượng
    indexed (11–116.088 byte) và missing (11–116.922 byte) tương đương nhau —
    không có filter dung lượng/định dạng nào giải thích được.
  - 1 document ledger `ready` (`wsc-927d7635…`) nhưng không có trong index —
    ca lẻ cần D2 đối chiếu khi ingest thật.
- Grep B1–B5 trên file (không qua index): **B1, B2, B3, B5 có đáp án trong
  file missing** (B1 hai file trùng nội dung; B2/B3 mỗi đáp án một file;
  B5 định nghĩa đủ `'0'/'1'` trong một file); **B4 không có mã ví dụ
  `Y302YL93020100` ở bất kỳ file nào** (chỉ có mã khác cùng dạng).
  → Ingest 83 file kỳ vọng sửa được **B1/B2/B3/B5**, **không kỳ vọng sửa B4**.
- Dry-run convert+chunk 83 file (không ghi): **+1.765 chunk mới, 1.467
  retrievable** (~4,3× index hiện tại). Cảnh báo: 580 chunk trùng text với
  index cũ (33%), 75 chunk lẫn XML thô, 10 file ≥ 50 chunk.
  Không file nào convert-fail hay 0 chunk.

## 1. Bảng đối chiếu 108 file

`indexed` = có `source_path` trong index (25); `missing` = không có (83).
Cột Chunks = số chunk trong index (missing luôn 0 theo định nghĩa).

| File | Bytes | Trạng thái | Chunks |
| --- | ---: | --- | ---: |
| wsc-015067b75dc12e2770b7d8cb.txt | 60 | missing | 0 |
| wsc-037c28842e209b28625d6157.txt | 1746 | indexed | 4 |
| wsc-09cd4af33dd4a4c9d0a348b2.txt | 9578 | missing | 0 |
| wsc-0bc9396d5a8435295af0813d.txt | 13130 | missing | 0 |
| wsc-0ce34911516dce8b4341458b.txt | 1516 | missing | 0 |
| wsc-0e854d56792f41ab0d643e71.txt | 2255 | missing | 0 |
| wsc-105d56e1feb8c98d73d2e695.txt | 9498 | missing | 0 |
| wsc-118d0600a2a94d418f2880ac.txt | 17894 | missing | 0 |
| wsc-11f5fbf5720d445b40967b4f.txt | 1353 | missing | 0 |
| wsc-1218b5b584c3da847fade6ec.txt | 81399 | missing | 0 |
| wsc-18c17803678e5d71f0cbb2ba.txt | 101 | missing | 0 |
| wsc-1b661fb170798e66bb7de3a1.txt | 14350 | missing | 0 |
| wsc-1b737eb997502d0f546982dc.txt | 116922 | missing | 0 |
| wsc-1c6b431a7eb8c5f13ce5e14c.txt | 9882 | missing | 0 |
| wsc-22ab58a4a087909fa305efb7.txt | 62 | missing | 0 |
| wsc-2d62e0b3a3ca889c7679ed93.txt | 5599 | indexed | 8 |
| wsc-2fd45ffa5e06424dc3fad52f.txt | 828 | missing | 0 |
| wsc-3756454c27e91ffade455f15.txt | 37851 | missing | 0 |
| wsc-38b2cd6236cebb3f18cd7f6f.txt | 7567 | missing | 0 |
| wsc-3b0a03602329b711cca4928c.txt | 4436 | missing | 0 |
| wsc-3e2d9b10662bbf7982e14e35.txt | 4951 | missing | 0 |
| wsc-42843eb6ca4459ae3af6b657.txt | 211 | missing | 0 |
| wsc-431e31fbbc3df5fc16f444cb.txt | 592 | missing | 0 |
| wsc-44dfba80a86aa4eaa987e2f2.txt | 2235 | missing | 0 |
| wsc-4600afa0ca80041712e8c65f.txt | 2242 | missing | 0 |
| wsc-48c40c0b3b6b5a4f1681f66d.txt | 3028 | indexed | 4 |
| wsc-4cbd21f3ccab9c9ea52161fa.txt | 378 | missing | 0 |
| wsc-4cc1bf837aa6c9844d67eb4c.txt | 19311 | missing | 0 |
| wsc-4ed67081b49075eed077ebf7.txt | 299 | missing | 0 |
| wsc-4f40ec64810753280ebcd83e.txt | 9702 | missing | 0 |
| wsc-5035a3d752d88cc0e20eb4c3.txt | 62329 | missing | 0 |
| wsc-50e045acef39dbcd38aff8fb.txt | 9702 | indexed | 20 |
| wsc-513068676f45d2e034f94508.txt | 828 | indexed | 2 |
| wsc-53124ddc95b374f1d58af350.txt | 9498 | missing | 0 |
| wsc-54179f47d8d2421b827912e2.txt | 81399 | indexed | 66 |
| wsc-54b55cadf3cc29c26169ed7c.txt | 134 | missing | 0 |
| wsc-5727edad788a579fde926c19.txt | 3028 | missing | 0 |
| wsc-575eb6de7d1db9ef0ac8afc8.txt | 877 | indexed | 1 |
| wsc-5b78db8c9cc2ad9844a9a0d7.txt | 23 | missing | 0 |
| wsc-5f2696c9a22072e7d4873267.txt | 39 | missing | 0 |
| wsc-5f357714c9ab95fe58b8fff6.txt | 34473 | missing | 0 |
| wsc-60f9c5ab578c69f2e474f5d9.txt | 39572 | missing | 0 |
| wsc-624b7034af500a849305d8bf.txt | 9498 | indexed | 22 |
| wsc-6349bfab87ce7a5eb246e10f.txt | 6348 | missing | 0 |
| wsc-638e2f76d300f8c32883b521.txt | 1142 | missing | 0 |
| wsc-65074328893666b1fbd9b4aa.txt | 18099 | missing | 0 |
| wsc-67d7ba0a3f56e527f5766ace.txt | 26973 | missing | 0 |
| wsc-6f049a1fdfc090dc7d439224.txt | 13181 | missing | 0 |
| wsc-72b177b9dab655fc0371095f.txt | 37851 | missing | 0 |
| wsc-73aa999fa4cdbafd7e6fdce8.txt | 48252 | missing | 0 |
| wsc-750990be3801b81970805644.txt | 2255 | indexed | 4 |
| wsc-762c79444401c88ae94adb61.txt | 11003 | indexed | 13 |
| wsc-762cd98f79d4ad1a0c235393.txt | 9578 | indexed | 22 |
| wsc-7a0194a6693a5a2b3bff1576.txt | 1652 | missing | 0 |
| wsc-803436a6d602b9775a3c0a44.txt | 13130 | missing | 0 |
| wsc-8782bf3e41a80998543bc9dd.txt | 134 | indexed | 1 |
| wsc-8ce71e2a14d81de80d196655.txt | 17894 | missing | 0 |
| wsc-90b85d5dd5c07833d2dfe481.txt | 5357 | indexed | 6 |
| wsc-9aadd66705d1772395adfc56.txt | 11 | missing | 0 |
| wsc-9abe0b8f8e644d009d771d5a.txt | 4926 | missing | 0 |
| wsc-9ace1acafb9d5869a4af01df.txt | 2235 | missing | 0 |
| wsc-9e9831c8c58795058809bf95.txt | 126 | missing | 0 |
| wsc-a36e39c1d9713f21dc65bcaf.txt | 696 | indexed | 1 |
| wsc-a6d76176e0998559e07f7072.txt | 26973 | indexed | 29 |
| wsc-ab150f1186115f64ca93a65d.txt | 43474 | missing | 0 |
| wsc-b1d2b7cf34341a3a2c854a42.txt | 43474 | missing | 0 |
| wsc-b2d92585a195357abb080c36.txt | 2255 | missing | 0 |
| wsc-b2fb28663b5d62bab155737c.txt | 1399 | missing | 0 |
| wsc-b4f7ba061c5c7e3bb4b84eb3.txt | 21397 | missing | 0 |
| wsc-b768543f75e10584eb1114b5.txt | 21397 | missing | 0 |
| wsc-b8220b0d1cc36804b19e6dea.txt | 116088 | indexed | 129 |
| wsc-be0e15bdc0524321e7587d7c.txt | 259 | missing | 0 |
| wsc-c0cfb5bb4e58b93f4ac06c76.txt | 27425 | missing | 0 |
| wsc-c6c41c4221c802bac0594a6d.txt | 696 | missing | 0 |
| wsc-c714c329588af1673186fed9.txt | 2922 | missing | 0 |
| wsc-c7377cc9661005aa4d35d54e.txt | 18223 | missing | 0 |
| wsc-ca0a6ec1c91d075519fb4edf.txt | 116088 | missing | 0 |
| wsc-d06bb85555fe25681f6216e9.txt | 877 | missing | 0 |
| wsc-d320e16fa80ee7e311b42fb7.txt | 1945 | indexed | 4 |
| wsc-d33a710608155df3811cc1d6.txt | 6348 | missing | 0 |
| wsc-d489e437c9abecd020ee12ba.txt | 18099 | missing | 0 |
| wsc-d527d90b5167a5a0b7acc55e.txt | 4005 | missing | 0 |
| wsc-d5721a7854185be7023fec63.txt | 4005 | indexed | 11 |
| wsc-d86e792838659a8a6ddc040e.txt | 4951 | indexed | 9 |
| wsc-da1844282c07cff93145d49f.txt | 68 | missing | 0 |
| wsc-def3e984eca9050e5d4413e6.txt | 14265 | missing | 0 |
| wsc-dfa96949730f7626d0996555.txt | 11003 | missing | 0 |
| wsc-e1c0fdd63cfe2a644a965d10.txt | 5357 | missing | 0 |
| wsc-e5f2338de8fbfdbd4faefe63.txt | 423 | missing | 0 |
| wsc-e9d27b6c728c286f2cf0ef93.txt | 9882 | indexed | 14 |
| wsc-eab6e69c0a9795201f575c88.txt | 230 | missing | 0 |
| wsc-edb70d31441621a7baaa28c2.txt | 2235 | indexed | 4 |
| wsc-ef0d393c086c7f07627ca8b8.txt | 14265 | indexed | 23 |
| wsc-ef469ab3d32e4c1060e9f947.txt | 1713 | missing | 0 |
| wsc-f131b2b0169443cf4e1dc576.txt | 4810 | indexed | 11 |
| wsc-f287d46f33966942d7ee887c.txt | 1652 | indexed | 4 |
| wsc-f49b5ae6e580acd55fb6a916.txt | 1746 | missing | 0 |
| wsc-f5a0db459cb8830edc7e2979.txt | 4810 | missing | 0 |
| wsc-f5e16c8261a4f585e58dd705.txt | 11 | indexed | 1 |
| wsc-f7276290ed2d6746fe646941.txt | 3329 | missing | 0 |
| wsc-f7803a0e6f985358687d3122.txt | 25489 | missing | 0 |
| wsc-f7c038c5298d57f6fc126895.txt | 1271 | missing | 0 |
| wsc-f824664c3f21c5cd6dfef082.txt | 42968 | missing | 0 |
| wsc-f9382a2ffe7275326a63cc91.txt | 5599 | missing | 0 |
| wsc-fb5c095f5d8bcfa80db7805b.txt | 830 | missing | 0 |
| wsc-fd3830a88383ab5017aeba54.txt | 1945 | missing | 0 |
| wsc-fdf051d0582fad7f5cf2fc18.txt | 18699 | missing | 0 |
| wsc-ff8304af86028eaa474a1706.txt | 15458 | missing | 0 |

Ghi chú bảng: đối chiếu 1–1 theo `source_path` (index) với tên file trên đĩa:
25 `indexed` / 83 `missing` / 108 tổng, khớp `SELECT DISTINCT` hai đầu.
Raw JSON đối chiếu ở `C:/Users/Admin/AppData/Local/Temp/d1_108.json` (máy
`h410asrock`, không commit).

## 2. Phân loại 83 file missing

Nguồn duy nhất cho phân loại: `source_preparation_ledger` trong
`workspace_chat.sqlite` (81 dòng: 32 `ready`, 49 `failed`) + đối chiếu
document_id với index (25) và đĩa (108).

- **Nhóm F — đã thử ingest và failed (6 file trên đĩa, thiếu trong index)**:
  `wsc-6349bfab87ce7a5eb246e10f` (B1, 34 attempts),
  `wsc-72b177b9dab655fc0371095f`, `wsc-803436a6d602b9775a3c0a44`,
  `wsc-ab150f1186115f64ca93a65d`, `wsc-b4f7ba061c5c7e3bb4b84eb3`,
  `wsc-d489e437c9abecd020ee12ba`.
  Lỗi: `bge_worker_prepare_stdout_eof` (worker chết khi prepare).
  Nhóm lỗi ledger chung: 40/49 failed là
  `preparation_init_bge_worker_init_stdout_eof`, 6 là prepare-stdout-eof,
  2 `semanticbackendunavailable`, 1 model-load-failed; attempt failed tới 106.
- **Nhóm N — chưa bao giờ vào ledger (77 file)**: không có dòng ledger nào,
  gồm toàn bộ file đáp án còn lại (B1-duplicate, B2, B3, B5-định nghĩa).
  Chưa từng được đưa vào pipeline trên máy này.
- **Không có manifest/allowlist**: không tìm thấy cấu hình giới hạn 25
  document; size hai nhóm chồng lấn hoàn toàn (indexed 11–116.088 byte,
  missing 11–116.922 byte; median ~4,8–5,0 KB) nên không có filter dung lượng;
  cùng đuôi `.txt`, cùng thư mục, nên không có filter định dạng.
- **Ca lẻ**: 1 document ledger `ready` nhưng không có trong index
  (`wsc-927d76353abd37bb72349dd8`) — D2 cần đối chiếu khi ingest thật
  (có thể ingest sau thời điểm index, hoặc commit thiếu chunk).
- Ledger còn 50 document_id không có file trên đĩa (collection cũ đã xóa) —
  ngoài phạm vi D1, ghi nhận để D2 khỏi nhầm.

## 3. Grep đáp án B1–B5 trên file

| Câu | Chuỗi | File chứa (đều missing khỏi index, trừ B5-một phần) |
| --- | --- | --- |
| B1 | `11922`/`12860`/`12626` | `wsc-6349bfab87ce7a5eb246e10f.txt` (nhóm F) + bản trùng nội dung `wsc-d33a710608155df3811cc1d6.txt` (nhóm N) |
| B2 | `YY2-Z151`/`YY2-Z152` | `wsc-5035a3d752d88cc0e20eb4c3.txt` (nhóm N, 62.329 byte) |
| B3 | `nvarchar(4000)` | `wsc-c0cfb5bb4e58b93f4ac06c76.txt` (nhóm N, 27.425 byte) |
| B4 | `Y302YL93020100` | **không file nào** (cả đĩa lẫn index) |
| B5 | `HOUSE_METHOD` + `'0'/'1'` | định nghĩa đủ trong `wsc-ff8304af86028eaa474a1706.txt` (nhóm N, 15.458 byte); các file khác chỉ nhắc tên trường |

Kết luận kỳ vọng: ingest 83 file sửa được **B1/B2/B3/B5** (đáp án nằm trong
file nhóm F/N, dry-run convert+chunk thành công — xem mục 4).
**B4 không kỳ vọng** vì mã ví dụ không tồn tại ở bất kỳ tầng nào trên máy này.

## 4. Dry-run ingest 83 file (không ghi)

Cách chạy: `scratch/d1_dryrun_ingest.py` (git-ignore, đã dùng xong) —
`ConverterRegistry.convert_document` + `StructureAwareChunker` y pipeline
(`max_chunk_chars=1200`), index thật chỉ mở `mode=ro` để lấy tập text cũ đối
chiếu trùng lặp. Không mở index ở chế độ ghi, không embed, không upsert.

- Phạm vi: 108 file trên đĩa, 83 missing (25 indexed bỏ qua).
- Kết quả: **+1.765 chunk mới, 1.467 retrievable** (trung bình ~21 chunk/file,
  ~18 retrievable/file). Không file nào convert-fail hay 0 chunk.
- File đáp án dry-run tốt: B1 hai file mỗi file 11 chunk/9 retrievable; B2 111
  chunk/84 retrievable; B3 79 chunk/78 retrievable; B5-định nghĩa 32 chunk/30
  retrievable.
- Cảnh báo (45 file có warning):
  - **580 chunk trùng text với index cũ (33%)** — trùng lặp nội dung giữa file
    mới và 25 document cũ (cao nhất 129 chunk ở một file; có cặp file trùng
    nhau như B1-duplicate). D2 cần dedupe hoặc chấp nhận near-duplicate.
  - **75 chunk lẫn XML thô** (`xmlns`/`<p:sld`) — đúng thứ tự đã chốt: KHÔNG
    dọn trong D1, dọn sau khi có baseline B trên corpus đầy đủ.
  - 10 file ≥ 50 chunk (lớn nhất 129 chunk) — ingest thật cần batch + resume
    như migration ONNX, tránh ôm toàn bộ trong một init worker.
- Raw: `d1_dryrun_files.json` + `d1_dryrun_warnings.json` ở Temp máy
  `h410asrock` (không commit).

## 5. Bàn giao D2 (chưa làm, chờ duyệt)

1. Backup mới index + verify `ok` (bắt buộc vì ghi thật).
2. Ingest 83 file theo batch có resume (ưu tiên 6 file nhóm F + 4 file đáp án
   nhóm N trước để có baseline B sớm), giữ nguyên 25 document cũ.
3. Verify: document/chunk/vector count, grep đáp án trong index, chạy lại
   B1–B5/H3 so baseline `484ac76`/`cc12d67`.
4. KHÔNG dọn XML trong D2 (làm sau, ticket riêng).

File báo cáo này: `docs/phieu-viec/ket-qua/FIX3_ingest-D1-dieu-tra.md`.
Commit riêng + push `phieu-viec/rag-fix1`, không merge `main`. DỪNG chờ duyệt.
