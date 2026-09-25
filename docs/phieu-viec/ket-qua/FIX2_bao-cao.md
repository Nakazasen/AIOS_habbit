# FIX 2 — Báo cáo ONNX int8 cho BGE-M3

## 1. Tóm tắt thay đổi

Thêm đường nhúng ONNX Runtime, không xoá đường PyTorch.

- `src/aios_habit/rag_v2/bge_onnx_backend.py`: `OnnxInt8BgeM3Backend` giữ `embed_documents` / `embed_query`, cộng `sparse_documents` / `sparse_query` vì hồ sơ hybrid đang dùng bắt buộc kênh sparse. Session dùng `CPUExecutionProvider`, `intra_op_num_threads` = số lõi CPU, `max_length` mặc định 512. Vector dense lấy token CLS rồi chuẩn hoá. Trọng số sparse lấy từ `sparse_linear.npy` theo đúng vòng lexical-weight của FlagEmbedding.
- `src/aios_habit/rag_v2/pipeline.py`: chỉ dựng backend này khi `BGE_BACKEND=onnx_int8`. Hồ sơ hybrid thiếu đầu sparse thì fail-closed, không bỏ kênh sparse im lặng. Hash tương thích index chỉ đổi khi flag bật, nên index PyTorch cũ không bị trộn vector.
- `src/aios_habit/rag_v2/bge_subprocess_worker.py`: nhánh init kiểm tra thư mục ONNX khi flag bật, và ghi `bge_backend` cùng thời gian init ra stderr.
- `src/aios_habit/rag_v2/retrieval_backends.py`: `verify_model_tree` ghi cache size/mtime cạnh thư mục model. Cache không nằm trong cây bị hash.
- `scripts/export_bge_m3_onnx.py`: lượng tử hoá int8 động từ ONNX fp32 đã có trong cây model, chép tokenizer, đổi `sparse_linear.pt` sang numpy, ghi checksum cạnh thư mục xuất.

## 2. Bảng benchmark trước/sau

Không có số liệu nhúng. Lượng tử hoá và so tốc độ embed chưa chạy.

Lý do đo được trên máy này, lúc bắt đầu FIX 2:

- RAM trống 3.75 GiB / 15.87 GiB (load 76%).
- ONNX fp32 đã có tại `local_runs/retrieval_models/bge-m3-5617a9f/onnx/` nặng khoảng 2.27 GiB dữ liệu ngoài. Nạp cả graph để `quantize_dynamic` sẽ vượt phần RAM trống.
- Gói `onnx` chưa cài. `onnxruntime.quantization` import thất bại vì thiếu `onnx`. `optimum` cũng chưa có trong môi trường.

Phần cache checksum thì đã đo, trên đúng cây BGE-M3 cục bộ (30 file, 4,587,317,404 byte):

| Lần | Việc | Giây |
| --- | --- | ---: |
| 1 | `sha256_model_tree` đọc hết cây | 44.877095 |
| 2 | `verify_model_tree` lạnh, chưa cache | 44.571067 |
| 3 | `verify_model_tree` khi size/mtime khớp pin | 0.031387 |

Lần 3 nhanh hơn lần hash đầy đủ khoảng 1430 lần. Đây không phải thời gian nhúng.

## 3. So sánh chất lượng

Chưa đo recall@10. Chưa embed một chunk thật ở `max_length` 512 và 2048, nên chưa có cosine giữa hai vector.

Đã kiểm tra công thức, không phải chất lượng model:

- `sparse_linear.pt` là `weight (1, 1024) float16` và `bias (1,) float16`. Script xuất ghi lại float32.
- Test `test_lexical_weights_keep_the_strongest_non_special_token` khoá vòng lấy trọng số lớn nhất, bỏ token đặc biệt.
- Test `test_onnx_backend_matches_cls_and_sparse_contract` khoá dense là CLS đã chuẩn hoá và sparse đi cùng một lần encode.

## 4. Kết quả `pytest tests/`

`pytest -q tests` trong 544.29 giây: **3119 passed, 3 skipped, 4 failed**. Không có test mới nào đỏ.

Bốn lỗi không nằm trong diff của FIX 2:

- `tests/test_commit_d_wheel_and_packaging.py::TestDependencyManifestLockIntegrity::test_uv_lock_check_succeeds`: `uv lock --check` báo lockfile cần cập nhật. `pyproject.toml` và `uv.lock` không đổi. Báo cáo FIX 1 đã ghi cùng lỗi này.
- `tests/test_commit_d_wheel_and_packaging.py::TestBgeM3ModelPackPackaging::test_bge_m3_model_pack_verification_and_discovery`: cây model cục bộ hash ra `sha256:697a97c33326734d8152b6f026297cd1421587039c301f52c39c34896bd40fda`, test cứng pin cũ `sha256:b1d887e…`. Hash này đo bằng `sha256_model_tree` trước khi ghi cache. Cache nằm ngoài thư mục model.
- `tests/test_commit_d_wheel_and_packaging.py::TestCleanMachineSmokeScript::test_clean_machine_full_isolated_venv_installation`: pip không tìm thấy `streamlit>=1.60.0` (from versions: none).
- `tests/test_mom_local_pilot.py::test_document_extractor_png_ocr_local_or_safe_unsupported`: chạy riêng thì **1 passed**. Lỗi trong bộ đầy đủ là lỗi phụ thuộc thứ tự đã ghi từ trước.

`scripts/check_docs.py` in `DOCUMENTATION_CONTRACT=PASS`.

## 5. Flag rollback

- `BGE_BACKEND`: mặc định không đặt, tức `pytorch`. Đặt `onnx_int8` để bật. Đặt lại `pytorch` hoặc xoá biến để về đường cũ.
- `AIOS_BGE_ONNX_MODEL_PATH`: mặc định `models/bge-m3-onnx-int8`.
- `AIOS_BGE_ONNX_MODEL_CHECKSUM`: pin `sha256:…`. Nếu trống, đọc file cạnh thư mục `<tên>.sha256`. Thiếu pin thì fail-closed.
- `AIOS_BGE_ONNX_MAX_LENGTH`: mặc định 512. Chỉ áp cho đường ONNX.
- Đường PyTorch và `bge_m3_max_length=2048` không đổi khi flag tắt.

## 6. Điểm khác với phiếu việc

- Phiếu đặt mặc định `BGE_BACKEND=onnx_int8`. Ràng buộc chung của phiếu, và cách FIX 1 đã làm, là mặc định giữ hành vi cũ cho tới khi người dùng bật. Flag này mặc định tắt. Chưa đạt nghiệm thu nên càng không được bật mặc định.
- Không gọi `optimum` để export lại từ PyTorch. Cây model đã có `onnx/model.onnx`. Export lại bằng torch sẽ nạp thêm bản 2.3 GiB trong khi máy chỉ còn 3.75 GiB trống.
- Hồ sơ `bge_m3_hybrid` cần sparse. Backend ONNX chỉ được nhận khi có `sparse_linear.npy`. ColBERT chưa xuất; hồ sơ `bge_m3_multivector` fail-closed trên đường này.
- `max_length=512` chỉ áp khi đường ONNX được chọn, không sửa mặc định PyTorch.

## 7. Đánh giá

Không đạt tiêu chí nghiệm thu của FIX 2. Chưa có bằng chứng tốc độ embed ≥ 2 lần, chưa có recall@10, chưa có cosine 512 so với 2048 trên model thật. Đường cũ vẫn là đường đang chạy. Code mới nằm sau flag tắt để lần sau, khi RAM trống đủ và đã cài `onnx`, chạy `scripts/export_bge_m3_onnx.py` rồi mới đo.
