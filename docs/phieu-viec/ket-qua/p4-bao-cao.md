# P4 — Chốt "bộ hằng số deploy" tái tạo đúng fingerprint `016c5255…` (KDTVN-PC0575)

- Ngày: 2026-09-29 (giờ máy, +07)
- Máy: `KDTVN-PC0575` (CPU-only); repo `D:\Sandbox\AIOS_habbit`, nhánh `phieu-viec/rag-fix1`
- Vé: `docs/phieu-viec/mailbox-pc0575/prompt.md` (ticket `p4-deploy-constants`, Muse viết 17:14)
- Ràng buộc vé: **CHỈ ĐỌC + TÍNH TOÁN** — không đổi biến môi trường nào trên máy, không restart app,
  không ghi index, không embed, không merge `main`. Đã tuân thủ (xem mục 6).
- Kết quả: **TÁI TẠO ĐƯỢC** — bộ 9 trường dưới đây băm ra đúng fingerprint đã seal; checksum deploy là
  `sha256:9f81075f…b11093` (cây ONNX fp32 máy nhà, sidecar FIX2), không phải checksum cây local PC0575.

## 0. Kết luận ngắn

| Trường (9 trường được băm) | Giá trị đúng |
|---|---|
| `artifact_checksum` | `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093` |
| `device` | `cpu` (lớp ONNX gán cứng) |
| `dimension` | `1024` |
| `distance` | `cosine` (hằng của `SemanticModelDescriptor`) |
| `model_id` | `BAAI/bge-m3` |
| `normalized` | `true` (gán cứng `True` trong lớp ONNX) |
| `revision` | `5617a9f61b028005a4858fdac845db406aefb181` |
| `runtime` | `onnxruntime-int8` (nhãn cứng của lớp ONNX fp32 — di sản tên cũ, xem ghi chú) |
| `runtime_version` | `1.28.0` (phiên bản `onnxruntime` đang cài trên PC0575) |
| **→ fingerprint** | **`016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`** (khớp 107.331 vector dense+sparse trong index) |

- Cơ chế đặt checksum cho vé sau: **sidecar `onnx.sha256`** (khuyến nghị, khớp sẵn cơ chế mã —
  `resolve_onnx_checksum`), không cần đụng env máy (mục 5).
- ⚠ **Điều kiện sống còn:** checksum `9f81075f…` chỉ hợp lệ khi **cây ONNX thật khớp đúng bytes** của nó
  (cây fp32 máy nhà `h410asrock`, `models/bge-m3-onnx-fp32`). Cây local PC0575 hiện tại
  (`local_runs\retrieval_models\bge-m3-5617a9f\onnx`) có hash **`728c9eb7…`** → khác; nếu dùng cây này thì
  fingerprint kỳ vọng là `8274fbb0…` (≠ sealed) ⇒ nguy cơ embed lại 107.331 vector (mục 5–7).

## 1. Fingerprint đầy đủ từ index production (bước 1 — chỉ đọc)

- Index: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
  (2.552.659.968 byte; mở bằng `sqlite3` URI `mode=ro`).
- Truy vấn: `SELECT model_fingerprint, COUNT(*) FROM chunk_embeddings GROUP BY 1 ORDER BY 2 DESC` (và bản
  tương tự cho `chunk_sparse_embeddings`):

| `model_fingerprint` | dense | sparse |
|---|---:|---:|
| `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` | 107.331 | 107.331 |
| `ce7fb53f797f0973e2cbf51d6a6ffef4de9a32b659b979f45663c6c360c8e43c` (PyTorch cũ, dead weight) | 340 | 340 |

- Vậy chuỗi mục tiêu đầy đủ 64 hex: **`016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`**.

## 2. Provenance lịch sử FIX2 trong `library.sqlite` (bước 2 — chỉ đọc)

- Liệt kê toàn bộ bảng trong index: `chunks`, `chunk_embeddings`, `chunk_sparse_embeddings`,
  `chunk_multivector_embeddings`, `chunks_fts` + 4 bảng phụ FTS. **KHÔNG có bảng metadata / manifest /
  migration / embedding-run nào.**
- Tuy nhiên **bảng vector tự lưu provenance per-vector**. `chunk_embeddings` có các cột:
  `model_id`, `model_revision`, `runtime`, `runtime_version`, `dimension`, `dtype`, `normalized`,
  `created_at` (+ `content_hash`). Một dòng mang fingerprint mục tiêu:

| Cột | Giá trị |
|---|---|
| `model_id` | `BAAI/bge-m3` |
| `model_revision` | `5617a9f61b028005a4858fdac845db406aefb181` |
| `runtime` | `onnxruntime-int8` |
| `runtime_version` | `1.28.0` |
| `dimension` | `1024` |
| `dtype` / `normalized` | `float32-le` / `1` |
| `created_at` | `2026-09-26T04:43:25.007646+00:00` (= 11:43:25 +07 ngày 26/09, thời FIX2/FIX3 máy nhà) |

- **Kết luận bước 2:** DB **KHÔNG lưu `artifact_checksum` và `device`** (và không có bảng manifest để tra).
  DB xác nhận 6/9 trường; 3 trường còn lại (`artifact_checksum`, `device`, `distance`) phải chứng minh bằng
  tái tạo (mục 3) đối chiếu nguồn ngoài DB:
  - `docs/phieu-viec/ket-qua/FIX2_bao-cao-may-nha-lan3.md`: sidecar máy nhà
    `models/bge-m3-onnx-fp32.sha256` = `sha256:9f81075f…b11093`;
  - `docs/phieu-viec/ket-qua/FIX3_baseline-D3-onnx.md`: "SHA-256 mô hình `9f81075f…`" + fingerprint `016c5255…`;
  - `docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`: worker chạy đúng cấu hình đó và ra đúng
    `016c5255…` khớp index.
- Nói chính xác: **không đoán** checksum — checksum lấy từ artefact nghiệm thu FIX2 và được kiểm chứng
  độc lập lại bằng hàm băm của mã (mục 3).

## 3. Tái tạo bằng `SemanticModelDescriptor.fingerprint` (bước 3 — thuần tính toán)

- Script (đã commit): `docs/phieu-viec/ket-qua/p4-tai-tao-fingerprint.py`
  (dùng trực tiếp `aios_habit.rag_v2.semantic.SemanticModelDescriptor`; không nạp model, không đọc model,
  không ghi gì; phần đọc index là SELECT `mode=ro`).
- Output nguyên văn (đã commit): `docs/phieu-viec/ket-qua/p4-ket-qua-tai-tao.json`.
- Quét **648 tổ hợp** trên tập ứng viên: 6 checksum × 3 device × 1 model_id × 3 runtime × 3 runtime_version
  × 2 revision × 1 dimension × 1 distance × 2 normalized. Kết quả: **2 tổ hợp khớp — nhưng cùng một tiền ảnh**
  (`device: "cpu"` và `device: ""`; `__post_init__` chuẩn hoá chuỗi rỗng thành `"cpu"`), tức **duy nhất một
  bộ giá trị hiệu dụng**, đúng bằng bảng mục 0.
- Tiền ảnh JSON (chuỗi được băm, `sort_keys=True`, `separators=(",", ":")`):

```json
{"artifact_checksum":"sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093","device":"cpu","dimension":1024,"distance":"cosine","model_id":"BAAI/bge-m3","normalized":true,"revision":"5617a9f61b028005a4858fdac845db406aefb181","runtime":"onnxruntime-int8","runtime_version":"1.28.0"}
```

- `sha256` của tiền ảnh = `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` = fingerprint mục 1.
- **Đối chứng (các checksum "gần" đều KHÔNG ra mục tiêu)** — cùng 8 trường còn lại:

| `artifact_checksum` thử | fingerprint | Khớp sealed? |
|---|---|---|
| `sha256:dad14a24…4bd4` (cây onnx PC0575, 8 file trước sparse head) | `0585bb9832edd15695e211e78c8de8a26c179cb9ce6e34ea63dc5bcd5942bde4` | Không |
| `sha256:728c9eb7…76baa` (cây onnx PC0575 hiện tại, 10 file) | `8274fbb05ec3ad6895bfc7a4a8cdd835d28317acf66b34e49f816ba5cab9bc3f` | Không |
| *(rỗng)* | `f6aff1c9fece53b4dbac856f28a86b6935fcd1d632afda99364641de0d37d89f` | Không |
| `sha256:b1d887e0…320b61` (pin manifest gói PyTorch) | `93c722cc7a79bfb92d30a84098480402c816c5c666e04f35a289c5fcff576fab` | Không |

- Ghi chú độ chính xác: `runtime = "onnxruntime-int8"` là **nhãn cứng** trong lớp ONNX của mã hiện tại
  (`bge_onnx_backend.py:260`) cho cả đường fp32; `device="cpu"` cũng cứng (`:265`); `runtime_version` chính là
  `importlib.metadata.version("onnxruntime")` (máy này: `1.28.0` — trùng thời điểm embed).

## 4. Mâu thuẫn manifest `b1d887e0` vs cây `728c9eb7` (bước 4 — kết luận)

- Hai bản manifest `src/aios_habit/bge_m3_manifest.json` và `packaging/models/bge_m3_manifest.json` có
  **nội dung JSON y hệt nhau** (đối chiếu `json.load` trong vé: `json_equal = True`; bản `packaging/models/`
  là bản canonical theo `model_pack.py:DEFAULT_MANIFEST_PATH`).
- Manifest này là của **gói model PyTorch fp32 đầy đủ** (repo HuggingFace BGE-M3), **KHÔNG phải int8** và
  **KHÔNG phải cây ONNX**:
  - `files` (12 file) toàn file PyTorch/HF: `pytorch_model.bin` (2.271.145.830 B), `colbert_linear.pt`,
    `sparse_linear.pt`, `tokenizer.json`, `imgs/`… — không có `model_quantized.onnx` (dấu hiệu int8) và
    cũng không có `model.onnx`/`model.onnx_data`/`*.npy` (cây ONNX).
  - `model_pack.verify_model_pack()` chỉ kiểm kích thước 12 file + `sha256_model_tree(root)` thuộc
    `approved_checksums`; `approved_checksums` = {`b1d887e0…`, `697a97c3…`}.
  - `697a97c3…` chính là hash cây model **đầy đủ cục bộ** `local_runs/retrieval_models/bge-m3-5617a9f`
    (30 file — cache verify `.bge-m3-5617a9f.aios-verify-cache.json` + báo cáo FIX2), còn `b1d887e0…` là
    pin gốc của gói. Cả hai đều thuộc **nhánh PyTorch/pack**, không liên quan nhánh ONNX.
- **Vì sao không phải là mâu thuẫn chặn deploy:** nhánh ONNX không đọc manifest này — nó đọc
  `AIOS_BGE_ONNX_MODEL_CHECKSUM` hoặc sidecar `onnx.sha256` (`resolve_onnx_checksum`), rồi
  `verify_model_tree` so với **cây ONNX**. Checksum deploy đúng vì vậy là `9f81075f…` (mục 3), không phải
  `b1d887e0…` (gói PyTorch) lẫn `728c9eb7…` (cây ONNX local PC0575).

## 5. Bộ hằng số deploy + cơ chế đặt checksum cho vé sau

**Bộ hằng số (đã chứng minh tái tạo — mục 3):**

| Hằng số | Giá trị |
|---|---|
| Thư mục ONNX (máy nhà đã nghiệm thu) | `models/bge-m3-onnx-fp32` (máy nhà `h410asrock`; FIX2 vòng 3) |
| Checksum cây (sidecar) | `sha256:9f81075f58fe1d251510d32ba5c9a66102f7420115519d3f720adc2348b11093` |
| `onnxruntime` | `1.28.0` (PC0575 đang cài đúng bản này) |
| `BGE_BACKEND` | mặc định (`onnx`) — **không** đặt `pytorch`, không cần đặt gì |
| `device` / `dimension` / `distance` / `normalized` | `cpu` / `1024` / `cosine` / `true` |
| `model_id` / `revision` | `BAAI/bge-m3` / `5617a9f61b028005a4858fdac845db406aefb181` |

**Cơ chế đặt checksum — khuyến nghị: sidecar** (khớp sẵn cơ chế mã, không đụng env máy):

- Mã: `resolve_onnx_checksum(model_dir)` (`bge_onnx_backend.py:102`): env `AIOS_BGE_ONNX_MODEL_CHECKSUM`
  **thắng** nếu có; nếu trống đọc sidecar `Path(model_dir).resolve().parent / f"{model_dir.name}.sha256"`
  (token đầu tiên; tự thêm tiền tố `sha256:` nếu thiếu; bắt buộc 64 hex).
- Với cây đặt tại **đường dẫn mặc định** `models\bge-m3-onnx-fp32` (hiện `ONNX_DIR_NAME = "bge-m3-onnx-fp32"`,
  `DEFAULT_BGE_BACKEND = "onnx"`): đặt sidecar `models\bge-m3-onnx-fp32.sha256` chứa
  `sha256:9f81075f…b11093`. Khi đó **không cần đặt env nào cả** — đúng cách đã nghiệm thu ở máy nhà.
- Với cây đặt tại `local_runs\retrieval_models\bge-m3-5617a9f\onnx` (vế vé gợi ý): sidecar tương ứng
  `local_runs\retrieval_models\bge-m3-5617a9f\onnx.sha256` — **chỉ đúng khi cây `onnx/` được thay bằng đúng
  bytes cây máy nhà** (hiện `onnx.sha256` chưa tồn tại và cây local hash `728c9eb7…`).
- ⚠ Hai chốt chặn của mã (fail-closed, đúng thiết kế):
  1. `verify_model_tree` **bắt buộc** hash thật của cây = checksum khai báo; lệch → worker chết, không embed
     (`local model checksum mismatch`).
  2. Nếu "cho chạy được" bằng checksum cây local (`728c9eb7…`): `_expected_backend_fingerprint` ra
     `8274fbb0…` ≠ sealed → app coi toàn bộ 107.331 vector hết hạn → **embed lại hàng loạt** (ước thô:
     ~2,5 s/chunk theo FIX3 D2 ⇒ 107.331 chunk ≈ 74 giờ) và ghi vào index production. **Cấm.**
- Kết luận: checksum đúng là `9f81075f…`, nhưng phải đi **kèm đúng cây model**; PC0575 hiện **chưa có**
  cây khớp (`models/bge-m3-onnx-fp32` không tồn tại; `models\` không tồn tại trên PC0575).

## 6. Tuân thủ ràng buộc + bằng chứng "không ghi"

- Không đổi env máy (chỉ đọc env qua `os.environ.get`; không `setx`/`SetEnvironmentVariable`).
- Không ghi index: mọi truy vấn `mode=ro`; index giữ nguyên `2.552.659.968` byte, mtime `2026-09-29 11:20:54`;
  thư mục index chỉ có `library.sqlite` (không sinh `-wal`/`-shm`).
- Không embed, không restart app, không merge `main`; không sửa code/runtime; script + output của vé chỉ
  tính toán và đọc.
- Cây model chỉ **được đọc** (hash lại cây onnx local = `728c9eb7…76baa`, 13,6 s — số đo tươi trong vé này,
  khớp cache verify + báo cáo P2-B7b).

## 7. Đề xuất vé sau (chờ Muse quyết — chưa làm)

1. **Mang đúng cây fp32 ONNX từ máy nhà sang PC0575** (`models/bge-m3-onnx-fp32`: `model.onnx` ~0,6 MB +
   `model.onnx_data` 2.266.886.160 B + tokenizer + `sparse_linear.npy`/bias — nguồn FIX2 vòng 3), verify
   `sha256_model_tree` = `9f81075f…`, đặt sidecar `models\bge-m3-onnx-fp32.sha256` → bật lại readiness
   (mong 171/171 nguồn `temporary` chuyển `ready`), kèm SHA-256 index trước/sau để chứng minh không ghi ngoài ý muốn.
2. Phương án thay thế (chỉ nếu user/Muse chấp nhận): **embed lại có kiểm soát** với hằng số cây local
   (`728c9eb7…`) — vé riêng, dry-run + backup + ước lượng thời gian/khối lượng theo quy ước; KHÔNG khuyến nghị
   (rủi ro vận hành lớn, ~74 giờ).
3. Không tự sửa hằng trong code/manifest; nếu Muse muốn cập nhật manifest/`model_pack` cho khớp thực tế thì mở
   vé riêng có test tương ứng.

## 8. Phụ lục — lệnh đã chạy

```text
# Bước 1+2 (probe read-only, scratch, gitignored): liệt kê bảng + provenance
uv run --no-sync --group dev python scratch/p4_db_probe.py

# Bước 3 (script commit): quét 648 tổ hợp, in JSON kết quả
uv run --no-sync --group dev python docs/phieu-viec/ket-qua/p4-tai-tao-fingerprint.py

# Đo tươi hash cây onnx local (chỉ đọc)
uv run --no-sync --group dev python -c "import sys; sys.path.insert(0,'src'); \
  from aios_habit.rag_v2.retrieval_backends import sha256_model_tree as h; \
  print(h(r'local_runs/retrieval_models/bge-m3-5617a9f/onnx'))"
# -> sha256:728c9eb7ee48a66ac4b6d567e3408433398911a6abcce9685d8a048eb8766baa (13,6 s)
```

- Kết quả JSON đầy đủ: `docs/phieu-viec/ket-qua/p4-ket-qua-tai-tao.json` (`status: REPRODUCED`,
  `checked_combos: 648`, `winners_count: 2` — cùng tiền ảnh, `counterfactuals` 4 dòng như mục 3).
- Định danh commit: xem `docs/phieu-viec/mailbox-pc0575/trang-thai.md` (dòng `Commit mới nhất`).
