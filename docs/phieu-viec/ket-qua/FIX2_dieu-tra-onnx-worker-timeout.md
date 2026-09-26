# FIX 2 follow-up — worker ONNX fp32 init timeout 300 s: chẩn đoán

Ngày: 2026-09-26. Hostname: `h410asrock`. Branch: `phieu-viec/rag-fix1`.
Chẩn đoán thuần túy: không sửa code, không retry vòng lặp nặng, không ghi index.

## Kết luận trước

Timeout không nằm ở bước verify/checksum hay ở việc mở onnxruntime session.
Bằng chứng probe cho thấy cold-start lần đầu của `OnnxInt8BgeM3Backend` trong
process chính mất ~62 s ở constructor (ngoài session/tokenizer/sparse head),
còn lần warm tiếp theo chỉ ~4 s. Worker subprocess có thêm các bước ngoài
backend init (tạo pipeline, mở index, `embedding_status()`), và bước
`_ensure_embeddings()` sẽ thấy toàn bộ 340 vector PyTorch hiện có là "thiếu"
đối với fingerprint ONNX mới (`016c5255…` thay vì `ce7fb53f…`), rồi cố embed
lại toàn bộ 340 chunk retrievable trên chính model ONNX vừa load — với tốc độ
lần đầu ~22,8 s/chunk đo được, 340 chunk cần hàng giờ, vượt xa timeout init
300 s. Phân loại: **(d) nguyên nhân khác — thiếu vector cùng fingerprint ONNX
kích hoạt re-embed toàn index ngay trong init**, không phải (a) verify 2,2 GB,
(b) session treo, hay (c) checksum fail-closed treo.

## 1. Chứng cứ hiện có

- Lần chạy timeout (điều tra B-sai): `BGE_BACKEND=onnx`,
  `AIOS_RAG_V2_SUMMARY_FIRST=1`, `AIOS_RAG_V2_SUMMARY_PROVENANCE=1`, config
  `index_read_only=True`/`ensure_embeddings_on_open=False`, 25 specs đã index.
  Client báo `bge_worker_init_timeout` sau 300 s; JSONL chỉ có event `env` +
  `specs`, không có event `init`, không có câu trả lời. File
  `bge_worker.stderr.log` của collection lúc đó rỗng (0 byte) — worker không
  kịp in cả dòng `bge_worker_stage`, hoặc stderr chưa flush trước khi client
  đóng process.
- Bối cảnh đã biết: FIX 2 vòng 3 benchmark trực tiếp trong process chính cho
  ONNX fp32 init **10,72 s** (lần đó model vừa export, máy rảnh ~8,2 GiB).
  Full suite gần đây có failures `test_bge_subprocess_client/worker`
  (`stdout_eof` lúc init) — cùng họ "worker chết lặng khi init", nhưng các test
  đó dùng PyTorch/chế độ khác, chỉ ghi nhận tương đồng triệu chứng, không kết
  luận cùng nguyên nhân.
- Model dir đủ: `models/bge-m3-onnx-fp32/` có `model.onnx` (565.924 byte) +
  `model.onnx_data` (2.266.886.160 byte), checksum sidecar
  `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`,
  cache verify sibling `.bge-m3-onnx-fp32.aios-verify-cache.json` tồn tại.

## 2. So sánh đường bench vòng 3 và đường worker (chỉ đọc code)

- Bench (`scripts/bench_fix2_onnx.py`): `resolve_onnx_model_path()` →
  `resolve_onnx_checksum()` → `OnnxInt8BgeM3Backend(...)` thẳng trong process
  chính, không mở index, không embed index, chỉ embed 20 query.
- Worker (`bge_subprocess_worker.py` init): `resolve_bge_backend_name()` →
  `resolve_onnx_model_path()` → `create_synthesis_provider()` →
  `RagV2DevPipeline(config)` → `pipeline.index.embedding_status()`.
- `RagV2DevPipeline.__init__` (`pipeline.py:568-583`): `_resolve_embedding_backend`
  (tạo `OnnxInt8BgeM3Backend`, trong đó `verify_model_tree` + `_open_session` +
  `_open_tokenizer` + sparse head) rồi mở `LocalChunkIndex`.
- `LocalChunkIndex.__init__` (`index.py:827-832`): chỉ gọi
  `ensure_embeddings()` khi `ensure_embeddings_on_open=True`; lần chạy timeout
  đã đặt `False` nên constructor không re-embed. Tuy nhiên worker gọi
  `embedding_status()` ngay sau đó ở phase `index_open`, và quan trọng hơn,
  **mọi query `bge_m3_hybrid` sau init đều đi `hybrid_search_with_summary` →
  `dense_candidates`/`sparse_candidates` với `ensure_embeddings=True`**, mà
  `dense_candidates` chỉ bỏ qua khi `self._read_only` (`index.py:2004`).
  Config read-only nên query cũng không ghi — nhưng `embedding_status()` và
  các bước warmup khác vẫn quét toàn bộ bảng vector để đối chiếu fingerprint.
- Khác biệt mấu chốt không phải env/cwd/session-options (cả hai đều
  `CPUExecutionProvider`, `ORT_ENABLE_ALL`, `intra_op=os.cpu_count()`,
  tokenizer `max_length=512`), mà là **worker init xong vẫn phải đứng trước
  một index mà 100% vector mang fingerprint PyTorch**, trong khi bench không
  hề chạm index.

## 3. Tái hiện tối thiểu (2 probe, mỗi lần ≤120 s, model dir read-only)

Probe 1 (`scratch/fix2_onnx_probe.py`, đã xoá sau dùng — scratch git-ignore):
gọi đúng `verify_model_tree` + constructor `OnnxInt8BgeM3Backend` + encode 1
câu ngắn, `BGE_BACKEND=onnx`:

```
[probe]  0.42s imports done (onnxruntime 1.28.0)
[probe]  0.42s verify done in 0.00s (cache sibling HIT)
[probe] 62.27s backend init done in 61.85s
[probe] 64.07s encode done in 1.80s dim=1024 → OK
```

Probe 2 (`scratch/fix2_onnx_probe2.py`): tách constructor thành sub-step:

```
verify 0.01s | _open_session 5.24s (RAM 5.41→4.52 GiB)
| _open_tokenizer 0.93s | sparse head 0.00s → OK 6.76s
```

Lần warm thứ ba (process khác): init **3,94 s**, encode đầu **22,76 s**.
RAM lúc probe 2: trống 5,44 GiB (ít hơn ~8,2 GiB lúc bench vòng 3).

Đọc kết quả:

- **Loại (a)**: verify cache HIT, 0,00–0,01 s. Không phải verify/hash 2,2 GB.
- **Loại (b)**: `_open_session` 5,24 s, không treo; tokenizer + sparse head
  ~1 s. Không phải session treo.
- **Loại (c)**: checksum/sparse head hợp lệ (`present=True`), không raise.
- Phần ~56 s còn lại của constructor cold-start nằm ngoài 3 sub-step trên
  (khởi tạo runtime/tokenizer native lần đầu trong process + page-in
  `model.onnx_data` 2,2 GB). Warm run sau đó chỉ ~4 s — đúng hành vi cold/warm,
  không phải treo cứng.
- Không có dấu hiệu tải mạng: mọi path đều local (`models/…`,
  `local_runs/retrieval_models/…`), không có log download.

## 4. Bước gây timeout: re-embed toàn index vì khác fingerprint (loại d)

- Vector hiện có trong index: 340 `chunk_embeddings` đều
  `model_id='BAAI/bge-m3'`, `runtime='flagembedding-pytorch'`,
  fingerprint `ce7fb53f797f…`; `chunk_sparse_embeddings` cùng fingerprint;
  đúng bằng 340 chunk retrievable.
- Fingerprint của backend ONNX fp32 đo trực tiếp: `016c5255d0ce…`
  (`runtime='onnxruntime-int8'`, 1.28.0) — khác hoàn toàn PyTorch.
- `_ensure_embeddings` (`index.py:1307-1326`) coi mọi row có
  `content_hash !=` hash text **hoặc khác `model_fingerprint`** là pending.
  Với backend ONNX mới, cả 340 row đều pending (sai fingerprint), nên sẽ gọi
  `embed_documents(340 text)` + `sparse_documents(340 text)`.
- Tốc độ ONNX lần đầu đo được: encode 1 câu ngắn **1,8–22,8 s** tùy
  warm/cold (bench vòng 3: 1631 ms/doc trên 20 query ấm). Kể cả lấy số lạc
  quan 1,6 s/chunk, 340 chunk ≈ 9 phút; lấy số cold 22,8 s/chunk ≈ 2,2 giờ.
  Cả hai đều vượt timeout init 300 s của client (và vượt cả
  `_INIT_TIMEOUT_SECONDS` mặc định nếu warmup đặt trong init).
- Đây là timeout **kiến trúc** (đổi backend = đổi fingerprint = toàn bộ vector
  cũ vô hiệu), không phải bug treo ở một dòng code. Worker PyTorch không gặp
  vì fingerprint trùng (`ce7fb53f…`), `pending` rỗng, init chỉ ~97–141 s
  (đã đo ở nghiệm thu lần 3) rồi trả lời ngay.

## 5. Hướng sửa cho vòng sau (không làm trong vòng này)

1. Không warmup/embed toàn index trong init ONNX: tách migration vector sang
   lệnh offline riêng (giống backfill provenance), chạy một lần với progress +
   timeout riêng, rồi mới cho worker ONNX đọc.
2. Nếu vẫn muốn lazy-migrate: `ensure_embeddings` theo batch nhỏ có giới hạn
   thời gian, hoặc chỉ embed khi query thực sự cần và báo degraded trong lúc
   migration chưa xong — thay vì để init 300 s ôm toàn bộ 340 chunk.
3. Ghi chú vận hành: lần đầu chuyển PyTorch→ONNX trên index có sẵn luôn tốn
   một lượt re-embed toàn corpus (ước tính từ tốc độ bench vòng 3); không nên
   đo latency ONNX-vs-PyTorch trên cùng index cũ mà chưa migrate vector.
4. Quan sát thêm: worker init ONNX nên log fingerprint + số pending vectors
   ngay trước warmup để lần sau phân biệt "treo" và "đang migrate".

## 6. Phạm vi và files

- Không sửa code; hai probe trong `scratch/` đã xoá (git-ignore). Không chạy
  benchmark nặng lặp lại; mỗi probe đúng 1 lần, có `timeout 120`.
- File báo cáo này: `docs/phieu-viec/ket-qua/FIX2_dieu-tra-onnx-worker-timeout.md`.
  Commit riêng + push `phieu-viec/rag-fix1`, không merge `main`. Sau đó dừng.
