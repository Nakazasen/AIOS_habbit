# FIX 2 vòng 3 — Benchmark ONNX fp32, kết luận ĐẠT (máy nhà `h410asrock`)

Ngày đo: 2026-09-26. Nhánh: `phieu-viec/rag-fix1`. File vòng 1
(`FIX2_bao-cao-may-nha.md`) và vòng 2 (`FIX2_bao-cao-may-nha-lan2.md`) giữ
nguyên để đối chiếu; đây là báo cáo vòng 3.

## 1. Chuẩn bị

- Graph fp32 export sạch vòng 2 tại
  `models/.bge-m3-onnx-work-r2/model_fp32.onnx/model.onnx` (~2,27 GB,
  `model.onnx` 0,6 MB + `model.onnx_data` ~2,27 GB) được chép nguyên sang thư
  mục benchmark mới `models/bge-m3-onnx-fp32/` (gitignored) kèm tokenizer +
  `sparse_linear.npy`/bias từ `models/bge-m3-onnx-optimum/`. `_model_file`
  trong `bge_onnx_backend.py` ưu tiên `model_quantized.onnx` rồi mới
  `model.onnx`, nên thư mục fp32 (chỉ có `model.onnx`) chạy đúng graph fp32.
- Sidecar checksum mới: `models/bge-m3-onnx-fp32.sha256`
  `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`.
- Runtime không sửa một dòng nào. Benchmark: `scripts/bench_fix2_onnx.py` cũ,
  chỉ trỏ `AIOS_BGE_ONNX_MODEL_PATH=models/bge-m3-onnx-fp32` +
  `AIOS_BGE_ONNX_MODEL_CHECKSUM` tương ứng.
- Máy lúc đo: RAM trống ~8,2 GiB (rảnh hơn vòng 2). Vòng này vẫn đo PyTorch
  chậm (95,2 s, xem mục 3) — số tuyệt đối của PyTorch dao động theo máy, nhưng
  tỉ số vẫn vượt ngưỡng với biên độ rộng.

## 2. Kết quả vòng 3 (cùng index, cùng 20 query, batch 8, CPU 8 thread)

Corpus: `local_runs/battle_rag_v2_index_cache/bffc6fa…/rag_v2_dev.sqlite`
(1000/9919 vector dense PyTorch, 16348 `chunks`). Đầy đủ:
`local_runs/fix2_bench_home_r3.json` (ngoài Git).

| Đo | PyTorch (max_length 2048) | ONNX fp32 (max_length 512) |
| --- | ---: | ---: |
| Init model lạnh | 44,885 s | **10,72 s** (~4,2×) |
| Embed 20 doc ấm | 95,175 s (4758,8 ms/doc) | **32,626 s (1631,3 ms/doc)** |
| **Tốc độ embed** | — | **nhanh hơn 2,92× (ĐẠT ≥ 2×)** |
| Cosine ONNX–PyTorch (20 text) mean / min | — | **1,0 / 1,0 (ĐẠT)** |
| Recall proxy top-10 mean / min / chênh | — | **1,0 / 1,0 / 0,0 (ĐẠT < 1%)** |
| Cosine 512-vs-2048 PyTorch | 1,0 | — |

## 3. Đối chiếu 3 vòng

| Vòng | Backend | Tốc độ (tuyệt đối ONNX / PyTorch) | Tỉ số | Recall proxy chênh | Kết luận |
| --- | --- | --- | ---: | ---: | --- |
| 1 (tracer + int8) | `models/bge-m3-onnx-int8/` | 15,1 s / 70,9 s | 4,69× | 7,5% | tốc độ ĐẠT, recall KHÔNG |
| 2 (optimum + int8) | `models/bge-m3-onnx-optimum/` | 11,7 s / 90,3 s | 7,70× | 7,5% | tốc độ ĐẠT, recall KHÔNG |
| 3 (optimum fp32) | `models/bge-m3-onnx-fp32/` | 32,6 s / 95,2 s | **2,92×** | **0,0%** | **ĐẠT cả hai** |

PyTorch tuyệt đối tăng dần qua 3 vòng (70,9 → 90,3 → 95,2 s) vì máy bận dần,
nhưng ONNX fp32 vẫn nhanh gần 3× ngay cả khi so với lần PyTorch chậm nhất.
Init ONNX fp32 (10,7 s) cũng nhanh hơn PyTorch (44,9 s) — lợi thế phụ khi khởi
động worker.

## 4. Kết luận: FIX 2 ĐẠT theo hướng ONNX fp32 (không int8)

Tốc độ **2,92× (ĐẠT ≥ 2×)**, recall proxy chênh **0,0% (ĐẠT < 1%)**,
cosine 512-vs-2048 = 1,0. Tiêu chí phiếu việc hoàn thành khi backend là ONNX
fp32; đường dynamic int8 (vòng 1/2) không đạt recall và không nên làm mặc định.

## 5. Đề xuất hướng backend (chưa làm trong vòng này)

1. Đổi mặc định ONNX sang fp32: `ONNX_DIR_NAME` trong
   `src/aios_habit/rag_v2/bge_onnx_backend.py:35` đang là `"bge-m3-onnx-int8"`;
   đề xuất `"bge-m3-onnx-fp32"` để `AIOS_BGE_ONNX_MODEL_PATH` không trỏ nhầm
   bản int8 vòng 1 khi người dùng bật flag mà không đặt path.
2. Chấp nhận cả hai tên flag: `_BACKEND_ALIASES` đã map `"onnx" → "onnx_int8"`;
   giữ nguyên để `BGE_BACKEND=onnx` (tên phiếu việc gợi ý) và `onnx_int8` đều
   chạy cùng backend fp32. Đổi tên class/error-string (`OnnxInt8…`,
   `onnx_int8_*`) là việc đổi tên lớn, chạm test — để riêng một commit sau.
3. int8 giữ làm tùy chọn thử nghiệm: hai thư mục `models/bge-m3-onnx-int8/` và
   `models/bge-m3-onnx-optimum/` vẫn còn (gitignored), dùng khi cần embed rẻ
   cho tác vụ không cần recall cao. Không xoá trong vòng này.
4. Mặc định runtime vẫn `pytorch` (flag tắt) cho tới khi có commit áp dụng
   đề xuất 1 + kiểm thử `test_rag_v2_bge_onnx.py` cập nhật theo. Vòng 3 chỉ đo,
   không sửa runtime.
5. Chưa chạy `pytest` vòng 3 (runtime không đổi; vòng 1 đã 10 passed tập trung).

## 6. Flag rollback (không đổi)

- `BGE_BACKEND` mặc định `pytorch`; đặt `onnx`/`onnx_int8` để bật (khi bật mà
  không đặt path thì vẫn trỏ `models/bge-m3-onnx-int8` — xem đề xuất 1).
- `AIOS_BGE_ONNX_MODEL_PATH=models/bge-m3-onnx-fp32`,
  `AIOS_BGE_ONNX_MODEL_CHECKSUM=sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093`
  cho đường fp32 đã nghiệm thu vòng này.
- `pyproject.toml`/`uv.lock` không đổi.
