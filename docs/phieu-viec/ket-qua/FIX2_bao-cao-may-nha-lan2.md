# FIX 2 vòng 2 — Export sạch bằng optimum, đo lại recall (máy nhà `h410asrock`)

Ngày đo: 2026-09-26. Nhánh: `phieu-viec/rag-fix1`. File vòng 1
(`FIX2_bao-cao-may-nha.md`) giữ nguyên để đối chiếu; đây là báo cáo vòng 2.

## 0. Snapshot venv trước khi làm (không đổi dependency)

- `local_runs/fix2r2_freeze_before.txt` (ngoài Git): `uv pip freeze` 159 dòng.
  Stack liên quan: `torch 2.5.1`, `transformers 4.44.2`, `tokenizers 0.19.1`,
  `FlagEmbedding`/`flagembedding 1.3.5`, `sentence-transformers 3.1.1`,
  `scikit-learn 1.9.0`, `pandas 3.0.5`, `pyarrow 24.0.0`, `onnx 1.17.0`,
  `optimum 1.24.0`, `onnxruntime 1.28.0`, `onnxscript 0.7.2`,
  `onnx-ir`/`onnx_ir 1.0.0`, `ml-dtypes 0.6.0`, `numpy 1.26.4`
  (freeze in 2 dòng `numpy==1.26.4` + `numpy==2.4.6` do dist-info 2.4.6 mồ côi
  còn kẹt từ sự cố `uv add` vòng 1 — `importlib.metadata` và `import numpy`
  đều báo đúng 1.26.4).
- Vòng 2 **không cài/không gỡ gói nào, không sửa `pyproject.toml`/`uv.lock`**.

## 1. Segfault sửa bằng cách nào

Nguyên nhân: BGE-M3 mang sidecar `config_sentence_transformers.json` +
`modules.json`/`sentence_bert_config.json`, nên
`TasksManager._infer_library_from_model_name_or_path` suy ra
`library_name="sentence_transformers"` (đã xác nhận bằng lệnh infer trực tiếp).
`get_model_from_task("feature-extraction", …)` vì thế load
`SentenceTransformer`, kéo chuỗi import `sentence-transformers` → sklearn →
pandas → **pyarrow 24.0.0 C-extension access violation** (faulthandler chỉ tới
`pyarrow/__init__.py:71` qua `pandas/compat/pyarrow.py`). Lỗi nằm ở import,
không phải ở model.

Cách sửa: ép `main_export(…, library_name="transformers")`. BGE-M3 bản chất là
encoder XLM-Roberta thuần (`config.json`: `XLMRobertaModel`, 24 lớp, hidden
1024, vocab 250002) nên `get_model_from_task(…, library_name="transformers")`
trả về `XLMRobertaModel` sạch, export xong trong 99,0 s, không segfault.
Không cần `TOKENIZERS_PARALLELISM=false` để sửa (vẫn đặt khi chạy cho chắc),
không cần `optimum-cli`, không cần hạ `pyarrow`, không đổi dependency.
Code: `_export_onnx_fp32_optimum` trong `scripts/export_bge_m3_onnx_optimum.py`
(đã sửa trong vòng này).

## 2. Export sạch + tiêu chí fp32 ≥ 0.999: ĐẠT (1,000000)

- Đích mới `models/bge-m3-onnx-optimum/` (gitignored), **không ghi đè**
  `models/bge-m3-onnx-int8/` vòng 1 để còn so sánh. Graph fp32 giữ tại
  `models/.bge-m3-onnx-work-r2/model_fp32.onnx/model.onnx` (~2,27 GB,
  gitignored). Sidecar checksum mới:
  `sha256:fab539b8503a9ddb448d78eb719712bd35f0da99331c4e5fd2bd65d23b82382a`.
- Cổng cosine fp32 (mới, `check_fp32_cosine` trong script export, chạy trước
  quantize, fail-closed nếu < ngưỡng): cosine(CLS fp32 ONNX, dense PyTorch
  `max_length=512`) trên 3 text thăm dò = **[1,0, 1,0, 1,0]**, worst
  **1,000000 ≥ 0,999** — export sạch, ĐẠT. (`main_export` optimum cũng tự ghi
  tokenizer/config hoàn chỉnh vào thư mục fp32.)
- Script export vòng này còn sửa: `_resolve_fp32_model` (optimum coi output là
  thư mục, ghi `model_fp32.onnx/model.onnx` chứ không phải file), và
  `export_tree` nhận `--min-fp32-cosine`/`--skip-fp32-check`.

## 3. Vòng 2 đo lại: tốc độ ĐẠT, recall vẫn KHÔNG ĐẠT

Cùng index, cùng 20 query, cùng corpus 1000 vector như vòng 1:
`local_runs/battle_rag_v2_index_cache/bffc6fa…/rag_v2_dev.sqlite`
(9919 `chunk_embeddings` / 16348 `chunks`). Kết quả đầy đủ:
`local_runs/fix2_bench_home_r2.json` (ngoài Git). Batch 8, CPU 8 thread.

| Đo | Vòng 1 (torch tracer + int8) | Vòng 2 (optimum sạch + int8) |
| --- | ---: | ---: |
| Cosine fp32–PyTorch (3 text) | không đo (không có graph fp32 sạch) | **1,000000** |
| Cosine int8–PyTorch mean / min (20 text) | 0,979218 / 0,976026 | **0,979218 / 0,976026** (giống hệt) |
| Recall proxy top-10 mean / min / chênh | 0,925 / 0,80 / 0,075 | **0,925 / 0,80 / 0,075** (giống hệt) |
| Tốc độ embed 20 doc | 4,69× (756 ms/doc) | **7,70×** (11,72 s vs 90,27 s; 586 ms/doc) |
| Cosine 512-vs-2048 PyTorch | 1,0 | **1,0** |

Lưu ý tốc độ: PyTorch vòng 2 chậm hơn vòng 1 (90,3 s vs 70,9 s) do máy bận lúc
đo; ONNX cũng nhanh hơn (11,7 s vs 15,1 s). Tỉ số 7,70× vì thế cao hơn 4,69×
nhưng cả hai đều vượt xa ngưỡng ≥ 2×. Init: PyTorch 29,2 s / ONNX 3,6 s.

## 4. Tách lỗi: export sạch, int8 là thủ phạm

- Hai graph int8 (vòng 1 tracer, vòng 2 optimum) cho cosine **giống hệt nhau**
  từng chữ số trên 3 text (`[0,984334, 0,977612, 0,983994]`) dù graph fp32 khác
  nhau — và cả hai đều lệch khỏi fp32 đúng **0,982775** trên cùng 1 text.
- Đổi `quantize_dynamic` sang full-int8 (bỏ `MatMulConstBOnly`) trên graph fp32
  sạch: cosine vẫn `[0,984334, 0,977612, 0,983994]` — y hệt. Lệch ~2% không đến
  từ exporter, không đến từ tùy chọn MatMul-only; nó đến từ bản chất dynamic
  int8 trên XLM-Roberta 24 lớp của BGE-M3.
- Hệ quả: recall proxy 0,925 (chênh 7,5%) là trần của đường int8 này, không
  phải do export bẩn. Muốn đạt recall chênh < 1% phải đổi hướng: giữ backend
  ONNX **fp32** (cosine = 1,0) và đo lại tốc độ — chưa làm trong vòng này.

## 5. Test

- Chưa chạy `pytest` trong vòng 2 (runtime `bge_onnx_backend.py`/`pipeline.py`
  không sửa; chỉ sửa script export/benchmark ngoài runtime). Vòng 1 đã có
  10 passed tập trung (`test_rag_v2_bge_onnx` + `test_rag_v2_numpy_dense`).
- `compileall` hai script sạch. `git diff --check` sạch (xác nhận trước commit).

## 6. Flag rollback (không đổi)

- `BGE_BACKEND` mặc định `pytorch`; `AIOS_BGE_ONNX_MODEL_PATH` mặc định
  `models/bge-m3-onnx-int8` (vòng 1). Thư mục vòng 2 `models/bge-m3-onnx-optimum`
  chỉ dùng khi trỏ flag tới; checksum sidecar tương ứng.
- `pyproject.toml`/`uv.lock` không đổi. Không thêm dependency mới.

## 7. Đánh giá

**FIX 2 vẫn CHƯA ĐẠT** nghiệm thu phiếu việc: tốc độ embed **7,70× (ĐẠT ≥ 2×)**,
cosine 512-vs-2048 = **1,0 (ĐẠT)**, export sạch cosine fp32 = **1,0 (ĐẠT)**,
nhưng recall proxy chênh **7,5% (KHÔNG ĐẠT < 1%)** và đã chứng minh trần này do
dynamic int8, không do export. Đường mặc định vẫn là PyTorch. Hướng tiếp theo
(chưa làm): benchmark backend ONNX fp32 (giữ cosine 1,0) xem tốc độ còn ≥ 2×
không; nếu có thì đó mới là đường đạt cả hai tiêu chí.
