# FIX 2 — Kiểm tra điều kiện máy nhà (chưa làm FIX 2)

Ngày kiểm tra: 2026-09-26. Hostname: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Phạm vi: chỉ kiểm tra điều kiện, không sửa code, không cài gói mới.

## 1. Model BGE-M3 local: CÓ, đủ file

- Đường dẫn code đang dùng (khớp cả hai nguồn):
  - `config/workspace_chat_rag_v2.local.json` → `model.path = D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f`
  - `.env` → `AIOS_BGE_M3_MODEL_PATH=D:\Sandbox\AIOS_habbit\local_runs\retrieval_models\bge-m3-5617a9f`
  - `revision = 5617a9f61b028005a4858fdac845db406aefb181` (khớp manifest)
- Tổng dung lượng thư mục: 2.295.419.991 byte (~2,14 GiB), trong đó `pytorch_model.bin` = 2.271.145.830 byte (~2,12 GiB). Đếm thực tế: **12 file**, không có thư mục con `onnx/`.
- Đối chiếu `packaging/models/bge_m3_manifest.json`: đủ 12/12 file theo tên
  (`config.json`, `config_sentence_transformers.json`, `modules.json`, `sentence_bert_config.json`,
  `special_tokens_map.json`, `tokenizer.json` (~17 MB), `tokenizer_config.json`,
  `sentencepiece.bpe.model` (~5 MB), `pytorch_model.bin`, `colbert_linear.pt`, `sparse_linear.pt`,
  `1_Pooling/config.json`) + thư mục `.cache/huggingface/download/1_Pooling` rỗng.
  Chưa hash SHA-256 toàn cây (việc này chính là bước `verify_model_tree` của FIX 2).
- **Điểm khác với máy công ty** (đọc từ `origin/phieu-viec/rag-fix1:docs/phieu-viec/ket-qua/FIX2_bao-cao.md` lúc push bị từ chối):
  máy công ty có **30 file / 4.587.317.404 byte**, gồm sẵn `onnx/model.onnx` (~2,27 GiB dữ liệu ngoài).
  Máy nhà này **không có** `onnx/` — script `scripts/export_bge_m3_onnx.py` của FIX 2 (commit `da3009b`)
  đi đường "quantize graph ONNX có sẵn", nên trên máy nhà sẽ thiếu nguồn vào và phải đi đường
  re-export từ PyTorch qua `optimum` (nặng RAM hơn) hoặc chép thư mục `onnx/` từ máy công ty sang.
- Ghi nhận thêm: thư mục reranker `local_runs/retrieval_models/bge-reranker-v2-m3` cũng tồn tại (~2,29 GB),
  nhưng theo phiếu việc reranker đã tắt, không đụng tới.

Kết luận: **CÓ** — đủ điều kiện nguồn model cho export ONNX.

## 2. RAM: ĐỦ

- Tổng RAM vật lý: 17.084.751.872 byte (~15,9 GiB). `TotalVisibleMemorySize` = 16.684.328 KB.
- RAM trống tại lúc đo: `FreePhysicalMemory` = 8.306.552 KB (~7,9 GiB). Đối chiếu: lúc làm FIX 2 trên
  máy công ty chỉ còn 3,75 GiB trống nên không quantize được — máy nhà hiện thoáng hơn gấp đôi.
- Ngưỡng FIX 2 cần: >6 GB trống để quantize graph ~2,27 GB.

Kết luận: **ĐỦ** — dư khoảng 2 GB so với ngưỡng. Lưu ý RAM trống dao động theo lúc đo;
nên đóng app nặng (Streamlit/Workspace Chat) trước khi chạy export/quantize.
Ổ đĩa: C: trống ~8,5/119,9 GB; D: (chứa repo) trống ~10,8/250,0 GB — đủ chỗ cho thư mục
đích `models/bge-m3-onnx-int8/` (hiện **chưa tồn tại**, FIX 2 sẽ phải tạo mới).

## 3. Gói Python: THIẾU `onnx`, `optimum` — CHƯA cài theo yêu cầu

| Gói | `.venv` | `.venv-rag` | `.venv-rag-compat` |
| --- | --- | --- | --- |
| `onnxruntime` | CÓ 1.28.0 | CÓ 1.28.0 | KHÔNG |
| `onnx` | KHÔNG | KHÔNG | KHÔNG |
| `optimum` | KHÔNG | KHÔNG | KHÔNG |

- `pyproject.toml` chỉ khai báo `onnxruntime>=1.20.0,<2.0.0` trong extra `rag-ingestion-cpu`;
  `uv.lock` chốt `onnxruntime 1.28.0`. Không có `onnx`/`optimum` trong dependency.
- Công cụ export đã có sẵn: `torch` (.venv 2.5.1 / .venv-rag 2.13.0 theo dist-info),
  `transformers` (.venv 4.44.2 / .venv-rag 4.57.6), `FlagEmbedding 1.3.5` — đường PyTorch hiện tại chạy được.
- Theo yêu cầu "thiếu thì chưa cài vội": **chưa chạy pip/uv add gì cả**.
  Khi làm FIX 2 cần thêm `onnx` + `optimum[onnxruntime]` (kèm pin phiên bản vào lockfile).

Kết luận: **THIẾU** 2 gói (`onnx`, `optimum`); `onnxruntime` đã đủ để chạy inference ONNX.

## 4. Index phục vụ benchmark recall@10 sau này

| File | Dung lượng | `chunk_embeddings` | `chunks` | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `local_runs/battle_rag_v2_index_cache/bffc6fac625657acdad91b172079034cb8ec0b6ac403ee48e6ae4f56ef8bd20d/rag_v2_dev.sqlite` | ~144,5 MB | 9919 | 16348 | Index FIX 1 đã dùng benchmark; vector thật BGE-M3 1024d — ứng viên tốt nhất cho recall@10 |
| `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` | ~27,4 MB | 1160 | 1397 | Collection `tri_thuc` thật của production |
| `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/workspace_chat.sqlite` | ~0,5 MB | 15 | 18 | Quá nhỏ, không dùng benchmark |
| `local_runs/workspace_chat_rag_v2_production/workspace_chat.sqlite` | ~53 KB | — (chỉ có `source_preparation_ledger`) | — | Không có vector |
| `local_runs/workspace_chat_rag_v2_canary/workspace_chat.sqlite` | ~45 KB | — (chỉ có `source_preparation_ledger`) | — | Không có vector |

Tất cả nằm trong `local_runs/` (ngoài Git), đếm bằng Bun SQLite read-only.

## 5. Ghi nhận remote (lúc push phát hiện branch đã tiến)

- `origin/phieu-viec/rag-fix1` đã có thêm 9 commit từ máy công ty, gồm FIX 2 (`da3009b`,
  đường ONNX int8 sau flag `BGE_BACKEND`, mặc định `pytorch`) và FIX 3 (`65cafe0`,
  summary-first sau flag `AIOS_RAG_V2_SUMMARY_FIRST`, mặc định tắt). Cả hai đều ghi rõ
  **chưa đạt nghiệm thu đo đạc** (FIX 2 thiếu RAM + thiếu `onnx`; FIX 3 xem `FIX3_bao-cao.md`).
- Báo cáo này cần rebase lên remote trước khi push, không ghi đè commit của máy công ty.

## 6. Kết luận chung

- Model: **CÓ** (đủ 12/12 file manifest, ~2,14 GiB, đúng revision) nhưng **THIẾU** `onnx/model.onnx` có sẵn như máy công ty.
- RAM: **ĐỦ** (~7,9 GiB trống > ngưỡng 6 GB; máy công ty lúc đó chỉ 3,75 GiB).
- Gói: **THIẾU** `onnx` + `optimum` (chưa cài); `onnxruntime 1.28.0` đã có ở `.venv` và `.venv-rag`.
- FIX 2 trên máy nhà khả thi hơn về RAM, nhưng phải giải quyết nguồn graph ONNX (re-export hoặc chép sang).
- DỪNG tại đây, chưa làm FIX 2, chưa cài gói mới.
