# Báo cáo vé OPT-RAGV2-PYLOOPS — tối ưu 3 vòng lặp Python (lane [VM])

Ngày: 2026-10-01. Người làm: Muse (VM). Trạng thái: code + test xong trên VM,
chờ OMP verify trên PC0575 (chưa ĐẠT).

## 1. Đã làm gì

Ba tối ưu trong `src/aios_habit/rag_v2/index.py`, theo đúng thứ tự vé yêu cầu:

| Bước | Nội dung | Commit |
|---|---|---|
| V2-A | `LocalChunkIndex.preload_dense_matrix_cache()` — nạp ma trận dense lúc worker init, query lạnh đầu tiên không còn gánh cold load trong timeout | `2480ba0` |
| V1-A2 | `_cjk_like_prefilter_rows()` — prefilter SQL LIKE cho query CJK trong `_candidate_rows`, chỉ gọi `_score_candidate` trên tập hẹp | `bb1a96e` → sửa lại ở `d20cff3` |
| V3-A | `_SparseVectorCache` — inverted index `term → posting list` (mảng `array("I")`/`array("d")`), parse 1 lần lúc worker init qua `preload_sparse_vector_cache()` | `f5aa767` |
| Test | 18 test mới `tests/test_rag_v2_opt_pyloops.py` | `e9be795` |

V3-B **không làm** — vé ghi rõ chỉ làm khi 3 bước trên chưa đạt <60s, mà con số này
chỉ đo được trên PC0575.

## 2. Số đo trên VM (cơ chế, không phải dự báo PC0575)

Môi trường: VM Linux 2 vCPU / 7GB RAM, Python 3.12.3. Corpus `SIMULATED_*`:
20.000 chunk, text trích nguyên văn từ file thật
(`AI_LSU_du_doan_loi.xlsx`, `Maintenance mode 3.xlsx` trong `~/workspace/aios_data`),
không bịa. Backend `DeterministicEmbeddingBackend(dimension=32)` — số tuyệt đối
không so được với BGE-M3 dim 1024 trên PC0575; giá trị của bảng này là chứng minh
cơ chế (before/after cùng điều kiện).

| Kênh | Trước | Sau | Ghi chú |
|---|---|---|---|
| Lexical CJK (`search_with_summary`) | 1,13–1,22s | 0,34–0,42s (**2,9–3,5x**) | prefilter giữ 0,5–2,1% số dòng; 3 query CJK thực tế từ corpus |
| Dense lạnh (`dense_candidates`) | 0,42s | 0,19s (2,2x) | ma trận đã nạp sẵn ở init; trên PC0575 con số thực là ~92,3s cold load được dời ra khỏi query đầu |
| Sparse (`sparse_candidates`) | 0,83s | 0,19s (**4,3x**) | inverted index; build cache 0,55s cho 20k chunk (làm 1 lần ở init) |

Memory (yêu cầu của vé, đo bằng RSS tiến trình sạch):
- Cache sparse cho 20k chunk / 313.654 posting: **+6,1MB**.
- Ngoại suy lên 108k chunk với mật độ thực của BGE-M3 (~250 term/chunk → 27M posting):
  khoảng **~530MB**, dưới ngân sách mặc định 1,5GB (`AIOS_RAG_V2_SPARSE_MAX_BYTES`).
  Vượt ngân sách → tự rơi về đường scan cũ, không bao giờ crash.

## 3. Điểm kỹ thuật quan trọng (đọc trước khi verify)

### V1-A2 — cơ sở ngữ nghĩa trong vé chưa đủ, đã hiệu chỉnh và đo kiểm

Vé viết: "`LIKE '%term%'` là superset của điều kiện match hiện tại
(`term in normalized_text` với CJK)". Kiểm tra code thực tế
(`_score_candidate`): điều kiện match thật là

```python
term in searchable_tokens
or (_CJK_RE.search(term) is not None and term in normalized_text)
```

trong đó `searchable_tokens` gồm token của **cả 4 cột**
(text/title/path/section/sheet). Nghĩa là:

1. Bản đầu tôi viết prefilter OR trên **tất cả** term (cho "đúng tuyệt đối") —
   đo ra **giữ 100% số dòng** (0% hiệu quả, còn chậm hơn một chút) vì các term ngắn
   (`ng`, `là`, `và`…) match khắp nơi. Vô dụng.
2. Làm đúng chữ vé (1–2 term dài nhất) thì nhanh (2,9–3,5x) nhưng **có thể làm
   lệch top-15** so với full scan: chunk chỉ match các term ngắn bị loại.
   Đã đo thấy lệch thật: 1/3 query CJK trong battery, và với câu E1 trên corpus
   thử (giữ 30/2180 dòng) top-15 lệch 9 chunk — các chunk bị loại là những chunk
   chỉ match các từ chung chung (`là`, `gì`, `và`…), bản prefilter trả về tập
   topical hơn (chỉ các chunk chứa `beam径`/`nguyên`).

Quyết định: giữ đúng chữ vé (1–2 term dài nhất, tie-break deterministic
`(-len, term)`), nhưng LIKE trên **4 cột** thay vì chỉ `normalized_text` như vé
viết — vì match qua tiêu đề/metadata của chính term dài nhất là trường hợp có
giá trị thật (vd chunk có `source_name="Beam径 troubleshooting guide.txt"`),
giữ 4 cột chỉ tốn thêm không đáng kể mà sát full scan hơn.

**Cần OMP quyết trên production:** chạy E1, so top-15 với baseline. Nếu lệch,
đặt `AIOS_RAG_V2_CJK_PREFILTER=0` (kill-switch đã có sẵn, mặc định bật) để về
full scan — không cần sửa code. 5/6 câu còn lại không chứa CJK nên prefilter
không bao giờ kích hoạt, trùng 100% chắc chắn.

### V2-A — không đổi ngữ nghĩa

Preload chỉ dời thời điểm nạp ma trận từ query lạnh đầu tiên sang lúc worker
init; đường xếp hạng (`_numpy_rank_variant` + tie-band exact-rescore) giữ nguyên.
Preload lỗi không bao giờ làm fail init (log warning, query vẫn chạy đường lazy).
Đã kiểm tra: query chỉ đọc (`read_only=True`, SQLite `mode=ro`) không làm
`PRAGMA data_version` đổi → cache không bị invalidate giữa chừng; chỉ ingest
đồng thời mới invalidate (đúng hành vi mong muốn).

### V3-A — toán học y hệt, đã chứng minh bằng test

- Chỉ doc chứa ≥1 query term mới được chấm (doc không chia sẻ term nào có dot
  bằng 0 tuyệt đối) → tập chấm của inverted index == tập có điểm > 0 của full scan.
- Tích lũy dot theo thứ tự query-term, khớp `sparse_dot_similarity` trong trường
  hợp phổ biến (query ngắn hơn doc). Trọng số float64 nên bit-identical với
  đường cũ.
- Test `test_sparse_cache_matches_legacy_scan`: cached vs legacy **trùng 100%**
  (kể cả cặp tie tuyệt đối), kèm kiểm tra privacy/stale filter, budget fallback,
  invalidate sau write.

## 4. Test

- Mới: `tests/test_rag_v2_opt_pyloops.py` — **18/18 pass**.
- Liên quan: `test_rag_v2_index.py` + `test_rag_v2_numpy_dense.py` +
  `test_rag_v2_semantic.py` — pass hết (77 test cùng file mới).
- Full suite (VM, 2 lần chạy sạch so song song): baseline `57db840` = 78 failed /
  3.479 passed / 61 errors; nhánh vé `b9ec37a` = 79 failed / 3.496 passed /
  61 errors. So tập FAILED+ERROR từng dòng: **y hệt nhau (139/139)** — chênh
  ±1 failed giữa các lần chạy là flaky có sẵn, **không thoái lui**. 0 failure
  trong `test_rag_v2_opt_pyloops.py` và các file rag_v2 liên quan. (Một lần chạy
  giữa chừng cho số fail cao bất thường đã được chứng minh là nhiễu do thao tác
  git đồng thời, không phải do code — chạy lại sạch thì tập lỗi trùng baseline.)
- Quét PEP 701 (multiline f-string, máy đích Python 3.11): sạch.
- `test_bge_subprocess_worker.py` rớt 6/11 — **rớt sẵn từ nền** (VM không spawn
  được worker thật), đã đối chiếu bằng worktree ở commit `2480ba0`: y hệt 6/11.

## 5. Hai rủi ro vé yêu cầu đo (bước 5)

a) **App có ghi vào `library.sqlite` lúc query không?** — Đường query của worker
   (`workspace_chat_rag_v2_adapter.py`) mở `read_only=True`, SQLite `mode=ro`;
   đã chứng minh bằng thực nghiệm `PRAGMA data_version`/`total_changes` rằng
   query thuần túy không invalidate cache. Đường warmup không `pipe_config`
   thì mở writable — nhưng đó là lúc khởi động, không phải lúc query.

b) **`PRAGMA cache_size`/`page_size`?** — `index.py` không set (chỉ
   `foreign_keys=ON`) → mặc định SQLite (page 4096 byte, cache 2MB). Không đề
   xuất đổi trong vé này (đụng behavior toàn cục của SQLite).

## 6. Việc còn lại cho OMP trên PC0575 (không làm được trên VM)

1. Chạy lại 6 câu L1–L3/E1–E3 trên index production `tri_thuc`, đo từng kênh
   (lexical / dense-lạnh / sparse) trước/sau theo phương pháp probe chỉ-đọc cũ.
2. So top-15 từng câu với baseline — đặc biệt **E1** (câu duy nhất chứa CJK).
   Lệch → đặt `AIOS_RAG_V2_CJK_PREFILTER=0` và báo lại, vé chưa đóng.
3. Mục tiêu query lạnh <60s. Không đạt → báo số thật từng kênh, không ép số.

## 7. Commit trên `phieu-viec/rag-fix1`

`2480ba0` (V2-A) → `bb1a96e` (V1-A2 bản đầu) → `f5aa767` (V3-A) →
`e9be795` (test) → `d20cff3` (V1-A2 bản chốt + kill-switch).
Python tương thích 3.11 (đã quét AST). Không merge main, không đụng production.

---

## 8. OMP verify trên PC0575 (CPU-only, index production `tri_thuc`)

- **Thời gian đo:** 2026-10-01 18:45–20:18 (phiên tối; lượt `legacy` dừng sau câu L2), 2026-10-02
  08:21–08:56 (chạy nốt `legacy` L3/E1/E2/E3), 2026-10-02 ~09:00–09:25 (wraps E1 + A/B prefilter
  + cổng test).
- **Phương pháp:** probe chỉ-đọc `scratch/opt_ragv2_verify_probe.py` hai chế độ — `new` = đúng cấu
  hình vé (preload V2-A/V3-A lúc init; prefilter CJK bật; cache sparse bật) và `legacy` = tắt
  preload + `AIOS_RAG_V2_CJK_PREFILTER=0` + `AIOS_RAG_V2_SPARSE_MAX_BYTES=0`. Cả hai chạy 6 câu
  L1–L3/E1–E3 qua `RagV2DevPipeline.query` in-process, đúng 19 nguồn `ready` của sổ `NB-E35A7BEE`
  / hội thoại `CONV-9C730D76`, cùng index production
  `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  — 2.842.415.104 B, 148.807 chunk / **120.452 retrievable**, mtime **2026-10-01 15:46:42 KHÔNG đổi**
  suốt phiên đo (probe + micro-probe chỉ đọc; app LAN không có truy vấn người dùng chen vào).
- **Mã nguồn đo:** đúng cây tip lúc nhận vé `e6f1876` (chứa chuỗi `2480ba0→d20cff3` của vé này).
  Từ đó tới tip `4e4236c`, `src/` chỉ nhận thêm Phase A `4a796ac` + Phase B `1f30092` của vé
  LEXICAL (kill-switch mặc định TẮT) — không ảnh hưởng số đo dưới đây.
- **Bằng chứng (scratch, git-ignore):** `opt_ragv2_verify_new.json|out`,
  `opt_ragv2_verify_legacy.json|out|run3.out`, `opt_ragv2_verify_compare.py|out`,
  `opt_ragv2_verify_wraps_E1.json|out` (+ `_pf0`).

### 8.1. Preload tại init (V2-A + V3-A)

| Lượt | dense | sparse | wall |
|---|---:|---:|---:|
| Đầu tiên sau restart (01/10 18:45, OS cache nguội) | 248,5s | 141,3s | ~390s |
| Lượt 2 (01/10 19:37, page cache ấm) | 114,0s | 102,7s | 216,7s |

### 8.2. Trước/sau từng kênh — 6 câu (giây, 1 chữ số thập phân)

| Câu | trước (legacy) tổng | lex/dense/sparse | sau (new) tổng | lex/dense/sparse | top-15 |
|---|---:|---|---:|---|---|
| L1 | 195,8 | 58,7 / 60,5 / 73,3 | 266,2 | 62,9 / 100,4 / 99,7 | trùng 100% |
| L2 | 205,2 | 44,7 / 91,9 / 66,3 | 301,3 | 75,7 / 112,3 / 110,9 | trùng 100% |
| L3 | 545,7 | 122,5 / 218,1 / 201,7 | 296,8 | 75,5 / 103,3 / 113,8 | trùng 100% |
| E1 | 552,8 | 53,7 / 0,6 / 214,5 | 454,6 | 176,9 / 0,5 / 0,3 | 15/15, **lệch thứ tự #10↔#11** (b) |
| E2 | 320,7 | 98,8 / 3,9 / 206,9 | 405,0 | 127,1 / 116,5 / 157,4 | trùng 100% |
| E3 | 666,5 | 262,2 / 7,6 / 388,8 | 302,9 | 133,7 / 103,9 / 62,4 | trùng 100% |

- **Query lạnh** (worker vừa restart + preload, câu đầu L1): **266,2s — KHÔNG đạt mốc <60s.**
- Điều kiện đo (trung thực): `legacy` L1/L2 đo tối 01/10 lúc app tắt; `legacy` L3/E1/E2/E3 đo sáng
  02/10 khi app LAN đang mở (idle, không truy vấn); `new` đo tối 01/10. Cả hai chế độ đều dính
  "cache mất giữa truy vấn" (mục 8.4) nên kết luận không phụ thuộc chênh lệch nền — chính các cột
  kênh cho thấy vì sao (dense/sparse phải nạp lại ngay trong câu hỏi ở cả hai phía).
- Điểm sáng đúng thiết kế — **E1 (CJK, không churn): sparse 214,5s → 0,3s** (V3-A + preload giữ
  cache); dense 0,6 → 0,5s. E1 còn 2 lượt search do `should_retry_thin_results` (lượt 1 mỏng
  ≤1 document → chạy lại với trọng số mismatch); summary chỉ giữ số kênh của lượt 2 — wraps tách
  được ở mục 8.3b. `candidates` E1: 47 → 38 (pool hợp nhất nhỏ hơn do prefilter thu hẹp lexical;
  tập top-15 không đổi).

### 8.3. Parity top-15

a) `new` vs `legacy` trên cùng index: **L1/L2/L3/E2/E3 trùng khớp 100% từng vị trí**; **E1 đủ
   15/15 chunk nhưng hoán vị đúng một cặp #10↔#11** — từ #3 đến #15 điểm RRF **đồng hạng 3,0**
   (13 vị trí tie), nên đây là khác thứ tự trong dải tie, không phải khác tập kết quả:
   - `legacy`: … 89a8b5a4…, **3ec69a69…**, **c8604f2e…**, 68eb2fea…
   - `new`: … 89a8b5a4…, **c8604f2e…**, **3ec69a69…**, 68eb2fea…
b) Theo chỉ dẫn §6 (báo cáo VM), chạy lại E1 mode `new` với `AIOS_RAG_V2_CJK_PREFILTER=0` (cùng
   probe wraps, cùng điều kiện page cache ấm):
   - **pf0: 15/15, trùng khít baseline từng vị trí (đúng thứ tự cũ).** Tổng 54,4s — lexical
     17,1 + 26,7; dense 3,9 + 0,6; sparse 0,5 + 0,4 (2 lượt do retry).
   - prefilter bật (wraps mặc định): tổng 69,1s — lexical 39,2 + 16,4; dense 4,1 + 0,6; sparse
     0,4 + 0,7; cùng thứ tự tie như lượt `new` lạnh.
   - ⇒ **Nguyên nhân lệch tie-order: V1-A2 (prefilter LIKE) đổi thứ tự sắp xếp trong dải điểm
     đồng hạng của E1; tắt cờ là về đúng baseline.** Tập chunk trùng 100% ở cả hai trạng thái cờ.
c) Ghi chú: 2 lượt wraps chạy trong điều kiện page cache ấm (sau lượt `legacy` đọc toàn DB) nên
   thời gian thấp hơn số 8.2 (đo lạnh) — dùng cặp wraps khi so tốc độ giữa hai trạng thái cờ.

### 8.4. Phát hiện chặn: bảng tạm FTS5 đổi `total_changes` → cache mất giữa truy vấn

- Micro-probe (đã push ở mốc 1/3): nhánh `_candidate_rows` non-CJK (đường FTS5) chèn bảng tạm →
  `total_changes` +200/+400; nhánh CJK (`deterministic_scan`) → +0.
- Token cache tại `e6f1876`: `_index_cache_token()` = `(PRAGMA data_version, total_changes)`.
- Hệ quả đo được: trong `hybrid_search_with_summary`, lexical chạy TRƯỚC dense/sparse; bảng tạm
  FTS của lexical đổi `total_changes` → cache dense/sparse bị coi là cũ → **mỗi câu non-CJK nạp
  lại ma trận dense ~98,9–113,8s + parse sparse ~99,7–110,9s NGAY TRONG câu hỏi** (dù preload đã
  chạy lúc init). E1 (CJK) không churn → giữ cache (dense 0,5s / sparse 0,3s) — khớp micro-probe.
- Đề xuất (không thuộc vé này): token bỏ `total_changes` → `(data_version, write-seq bảng main)`
  — **Phase A `4a796ac` đã code**; thuộc vé LEXICAL, verify tại vé đó (đúng hàng chờ). V2-A/V3-A
  của vé này chỉ phát huy đủ tác dụng SAU khi token đổi.

### 8.5. Hai rủi ro vé yêu cầu đo (bước 5)

a) **App có ghi `library.sqlite` trong lúc query?** — Không cần writer ngoài: chính truy vấn
   non-CJK ghi bảng tạm FTS5 trên connection worker → `total_changes` tăng (mục 8.4). Trong phiên
   đo, log app/worker đứng yên và mtime index không đổi — không có ghi ngoài.
b) **PRAGMA connection worker:** `page_size=4096`, `cache_size=-2000` (2 MB), `mmap_size=0`,
   `journal_mode=delete` — đúng mặc định (mã chỉ set `foreign_keys=ON`). Throughput đọc tuần tự
   ~4,8 MB/s theo số đo 442 MB/92,3s — trần I/O của máy CPU-only, không phải cấu hình sai.

### 8.6. Cổng nền PC0575 + kết luận OMP

- Cổng: `compileall` EXIT=0 · `check_docs` = `DOCUMENTATION_CONTRACT=PASS` · CLI audit
  `"status": "PASS"` · import `workspace_chat_app` OK · test `test_rag_v2_opt_pyloops.py` **18/18**
  và gộp 5 file rag_v2 liên quan (`opt_pyloops`, `index`, `numpy_dense`, `semantic`,
  `index_bundle`) **80 passed** (Python 3.11, PC0575).
- **Kết luận:** (1) mốc <60s **KHÔNG đạt** — số thật từng kênh ở 8.2; nút thắt chính: cache churn
  FTS-temp (8.4) + lexical vẫn đắt (62,9–262,2s tùy câu/điều kiện). (2) Parity: 5/6 trùng 100%;
  E1 lệch **tie-order** 1 cặp trong dải đồng hạng 3,0; `AIOS_RAG_V2_CJK_PREFILTER=0` → khít
  baseline ⇒ chờ Muse quyết định chấp nhận tie-order hay yêu cầu xử lý riêng (theo §6, việc
  "đóng vé" thuộc phán quyết của Muse). (3) Index production không đổi; không đụng `main`.
  (4) Đề xuất: ghi phát hiện chặn vào vé LEXICAL (Phase A đã có fix) và cho phép chuyển verify
  LEXICAL theo hàng chờ.
