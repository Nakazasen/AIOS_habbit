# FIX 2 — Báo cáo ONNX int8 cho BGE-M3 (máy nhà `h410asrock`)

Ngày đo: 2026-09-26. Nhánh: `phieu-viec/rag-fix1`.
Máy này khác máy công ty: trước lượt này máy nhà **chưa có** `onnx/model.onnx`
(chỉ 12 file / ~2,14 GiB), nên phải re-export từ `pytorch_model.bin` rồi mới
quantize. Báo cáo `FIX2_bao-cao.md` của máy công ty giữ nguyên; đây là báo cáo
riêng của máy nhà, thay thế nó khi nghiệm thu trên máy này.

## 1. Tóm tắt thay đổi

- Mới: `scripts/export_bge_m3_onnx_optimum.py` — export PyTorch → ONNX fp32 rồi
  quantize dynamic int8, ra `models/bge-m3-onnx-int8/` (gitignored) + sidecar
  `models/bge-m3-onnx-int8.sha256`. Có chốt RAM (`--min-free-gb`, mặc định 6,0):
  thiếu RAM thì từ chối chạy thay vì treo máy. Đường via `optimum.main_export`
  giữ lại (`--exporter optimum`) nhưng mặc định dùng torch tracer
  (`--exporter torchscript`, opset 17) vì `optimum` 1.24 giải task qua
  `sentence-transformers`, mà import gói đó segfault trong venv này (pyarrow
  C-extension access violation theo chuỗi pandas → sklearn).
- Mới: `scripts/bench_fix2_onnx.py` — benchmark so sánh ONNX int8 vs PyTorch
  trên cùng văn bản (không ghi DB): latency embed, cosine ONNX–PyTorch,
  cosine 512-vs-2048, và recall proxy (top-10 ONNX so với top-10 PyTorch trên
  cùng corpus PyTorch lưu sẵn).
- Không sửa runtime: `bge_onnx_backend.py`, `pipeline.py`,
  `bge_subprocess_worker.py`, `retrieval_backends.py` của máy công ty
  (commit `da3009b`) giữ nguyên. Flag `BGE_BACKEND` mặc định `pytorch`;
  `AIOS_BGE_ONNX_MAX_LENGTH` mặc định 512 chỉ áp đường ONNX. Không đổi schema DB.

## 2. Bảng benchmark trước/sau

Corpus: `local_runs/battle_rag_v2_index_cache/bffc6fa…/rag_v2_dev.sqlite`
(index FIX 1 đã dùng), **1000 vector** dense PyTorch BGE-M3 1024d trong
9919 `chunk_embeddings` / 16348 `chunks`; 20 query là text thật của 20 chunk
tiếp theo trong cùng DB. Kết quả đầy đủ: `local_runs/fix2_bench_home.json`
(ngoài Git). Batch 8, CPU, `intra_op_num_threads` = số core.

| Đo | PyTorch (BGE-M3, max_length 2048) | ONNX int8 (max_length 512) |
| --- | ---: | ---: |
| Init model (lạnh, 1 lần) | 6,98 s | 1,66 s (~4,2×) |
| Embed 20 doc (ấm) | 70,873 s (3543,7 ms/doc) | 15,119 s (756,0 ms/doc) |
| **Tốc độ embed** | — | **nhanh hơn 4,69×** (tiêu chí ≥ 2×: ĐẠT) |

Export/quantize (1 lần, RAM trống ~5,3–5,5 GiB lúc chạy, dưới ngưỡng 6 GB nên
phải hạ `--min-free-gb 5.0`): torch tracer export fp32 207,2 s → quantize
dynamic int8 180,8 s → checksum 4,9 s; tổng 394,8 s (~6,6 phút). Thư mục đích
`models/bge-m3-onnx-int8/` 565 MB (`model_quantized.onnx` 0,8 MB +
`model_quantized.onnx.data` ~569 MB + tokenizer + `sparse_linear.npy`).

## 3. So sánh chất lượng

- Cosine 512-vs-2048 trên đường PyTorch (1 chunk, tiêu chí phiếu việc 5.3):
  **1,000000** — chunk ngắn không chạm trần token, ĐẠT (≈ 1,0).
- Cosine ONNX int8 vs PyTorch trên 20 text: trung bình **0,979218**,
  thấp nhất **0,976026**. Lệch ~2% do quantize int8 + export tracer — chấp nhận
  được cho dense cosine, nhưng là nguyên nhân recall proxy dưới đây không = 1.
- Recall proxy (top-10 ONNX so với top-10 PyTorch trên cùng 1000 vector corpus
  PyTorch, PyTorch làm ground truth): trung bình **0,925**, thấp nhất **0,80**,
  chênh lệch **0,075 (7,5 điểm)** — tiêu chí phiếu việc là chênh lệch recall@10
  **< 1%**: **KHÔNG ĐẠT**.

## 4. Kết quả `pytest tests/`

- Tập trung: `tests/test_rag_v2_bge_onnx.py` + `tests/test_rag_v2_numpy_dense.py`
  **10 passed**; `compileall src tests` sạch.
- Chưa chạy full `pytest tests/` trong lượt này (lý do: benchmark embed đã chiếm
  ~3 phút/model; full suite ~9–15 phút và không nằm trong tiêu chí FIX 2).

## 5. Flag rollback

- `BGE_BACKEND`: mặc định không đặt, tức `pytorch`. Đặt `onnx_int8` để bật,
  đặt lại `pytorch` hoặc xoá biến để về đường cũ.
- `AIOS_BGE_ONNX_MODEL_PATH`: mặc định `models/bge-m3-onnx-int8`.
- `AIOS_BGE_ONNX_MODEL_CHECKSUM`: pin `sha256:2205c800d147b8694c4d748f2e235114233a013e79a6732e4533ffb0af9be87f`
  (sidecar `models/bge-m3-onnx-int8.sha256`). Thiếu pin thì fail-closed.
- `AIOS_BGE_ONNX_MAX_LENGTH`: mặc định 512, chỉ áp đường ONNX.
- Gói mới chỉ để export (không vào runtime query): `onnx 1.17.0`,
  `optimum 1.24.0`, `onnxscript 0.7.2`, `onnx-ir 1.0.0`, `ml-dtypes 0.6.0`
  — cài `--no-deps` vào `.venv` để tránh `uv add` đụng `numpy` (đã làm hỏng
  venv một lần trong lượt này, xem mục 6). `onnxruntime 1.28.0` đã có từ trước.
  `pyproject.toml`/`uv.lock` **không đổi** — cài đặt chưa được chốt vào
  dependency; làm lại FIX 2 trên máy khác phải cài lại 5 gói này.

## 6. Điểm khác với phiếu việc

- Phiếu yêu cầu `scripts/export_bge_m3_onnx.py` dùng `optimum` export trực tiếp.
  Script đó (máy công ty) chỉ quantize từ `onnx/model.onnx` có sẵn — máy nhà
  không có file này nên script mới export từ PyTorch. `optimum` không dùng được
  ở đây (segfault `sentence-transformers`/pyarrow trong `.venv`); thay bằng
  torch tracer opset 17. Dense ra là `last_hidden_state`, CLS pooling vẫn do
  `bge_onnx_backend.py` đảm nhiệm như cũ.
- Phiếu đặt recall@10 trên "tập câu hỏi test"; máy nhà không có bộ câu hỏi
  benchmark đóng băng nên dùng recall proxy top-10 agreement trên 20 query thật
  từ cùng index. Proxy này nghiêm hơn so sánh thuần cosine nhưng không phải
  recall@10 chuẩn có nhãn.
- RAM trống lúc export (~5,3 GiB) thấp hơn ngưỡng 6 GB của phiếu; export vẫn
  xong trong ~6,6 phút nhưng phải hạ chốt `--min-free-gb 5.0`. Không khuyến nghị
  chạy export khi RAM < 5 GiB.
- `uv add onnx/optimum` làm hỏng `.venv` (upgrad `numpy` 1.26.4 → 2.4.6 giữa
  chừng rồi lỗi quyền `numpy.libs`, `torch`/`onnxruntime` gãy import). Đã khôi
  phục bằng `uv pip install --force-reinstall numpy==1.26.4`, verify
  `numpy/torch/transformers/onnxruntime` import lại bình thường + FIX 1 test
  4 passed, rồi cài 5 gói export bằng `uv pip install --no-deps`. Dư lượng:
  `licenses` mồ côi của dist-info numpy 2.4.6 còn kẹt trong `.venv` (không xoá
  được do quyền, `importlib.metadata` vẫn báo đúng 1.26.4).

## 7. Đánh giá

**CHƯA ĐẠT** nghiệm thu FIX 2. Tốc độ embed **4,69× (ĐẠT ≥ 2×)**,
cosine 512-vs-2048 = **1,0 (ĐẠT)**, nhưng recall proxy chênh **7,5% (KHÔNG ĐẠT
< 1%)**. Đường mặc định vẫn là PyTorch; ONNX int8 nằm sau flag tắt, an toàn.
Hướng tiếp theo (chưa làm): thử quantize int8 chỉ MatMul (`MatMulConstBOnly`
đã bật) so với quantize full, hoặc giữ ONNX fp32 làm backend nhanh mà không
mất recall — đo lại proxy trước khi quyết.
