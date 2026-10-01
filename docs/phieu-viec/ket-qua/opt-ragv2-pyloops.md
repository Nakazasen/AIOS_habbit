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
- Full suite: đang chạy, so với nền sau (kết quả sẽ bổ sung trước khi đóng vé).
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
