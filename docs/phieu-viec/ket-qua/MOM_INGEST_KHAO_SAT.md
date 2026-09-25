# Báo cáo khảo sát ingest tài liệu MOM vào RAG v2 bằng BGE-M3

Ngày khảo sát: 2026-09-25
Nhánh: `phieu-viec/rag-fix1`
Phạm vi: chỉ đọc, không sửa mã nguồn. Chỉ truy vấn siêu dữ liệu index (số lượng, tên nguồn, kích thước vector, thời gian), không trích nội dung chunk.

## 1. Index đã kiểm tra

Đường dẫn gợi ý trong nhiệm vụ (`local_runs/battle_rag_v2_index_cache/*/rag_v2_dev.sqlite`) **không tồn tại** trên nhánh này.

Index RAG v2 đang dùng thực tế:

| Tệp | Dung lượng | Sửa đổi lần cuối | Vai trò |
|---|---|---|---|
| `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/workspace_chat.sqlite` | 51.154.944 byte | 2026-09-25 10:09:16 | **Index chính**: chunk, vector dày BGE-M3, vector thưa, FTS |
| `local_runs/workspace_chat_rag_v2_canary/workspace_chat.sqlite` | 397.312 byte | 2026-09-25 10:15:24 | Sổ cái chuẩn bị nguồn (`source_preparation_ledger`), không chứa vector |

Căn cứ mã nguồn: `src/aios_habit/workspace_chat_rag_v2_adapter.py` dòng 157 đặt gốc chạy mặc định là `local_runs/workspace_chat_rag_v2_canary`, hồ sơ duy nhất được phép là `bge_m3_hybrid` (dòng 158). `src/aios_habit/rag_v2/pipeline.py` dòng 196 khai báo `bge_m3_dimension = 1024`.

## 2. Số chunk, số tài liệu, kích thước vector

Truy vấn trực tiếp index chính ở chế độ chỉ đọc:

- Tổng số chunk trong bảng `chunks`: **2497**.
- Chunk dùng được (`retrievable = 1`): **2132**. Còn lại 365 chunk là bản mẹ không dùng truy hồi trực tiếp.
- Số tài liệu nguồn phân biệt (`document_id`, `source_path`, `source_name` đều trùng nhau): **93**.
- Số vector dày trong `chunk_embeddings`: **2132**, khớp đúng số chunk dùng được.
- Số vector thưa trong `chunk_sparse_embeddings`: **2132**. Vector đa biểu diễn: 0.
- Mô hình nhúng ghi trong từng bản ghi vector: `model_id = BAAI/bge-m3`, `model_revision = 5617a9f61b028005a4858fdac845db406aefb181`, `dimension = 1024`, `dtype = float32-le`, `normalized = 1`.
- Kiểm tra thực tế 5 vector mẫu: cột `dimension` đều 1024, `LENGTH(vector_blob)` đều 4096 byte, tức 1024 × 4 byte. **Đúng là embedding BGE-M3 1024 chiều.**
- Mô hình BGE-M3 có sẵn trên máy tại `local_runs/retrieval_models/bge-m3-5617a9f` (gồm `pytorch_model.bin` khoảng 2,27 GB và thư mục `onnx` với `model.onnx`), mã bản in trùng với `model_revision` trong index.
- Thời gian ingest vector dày: từ `2026-08-21T08:19:14Z` tới `2026-09-24T10:54:17Z`. Lần ingest gần nhất: **2026-09-24 10:54:17 giờ UTC**.
- Sổ cái chuẩn bị nguồn có 1136 mục: 66 `ready`, 945 `failed`, 125 `pending`.

Lưu ý cách định danh: tài liệu trong index mang mã `wsc-<24 ký tự>` bằng hàm băm SHA-256 của văn bản đã trích xuất (`_document_id` trong `workspace_chat_rag_v2_adapter.py` dòng 636-646), tên tệp gốc không nằm trong index mà nằm ở thư viện ca làm việc (`local_cases/workspace_chat/notebook_sources.jsonl` 640 bản ghi và `temporary_sources.jsonl` 644 bản ghi). Đối chiếu dưới đây nối tên tệp gốc với mã `wsc-*` bằng đúng hàm băm này.

## 3. Bảng đối chiếu 12 tệp MOM

| Mã | Tệp MOM cần đối chiếu | Trong index | Bằng chứng |
|---|---|---|---|
| F01 | AMS概略フロー_入出庫・生産_20250703VN.pdf | Có | Thư viện có `SRC-AED61712` (trạng thái `ready`, tên thực `AMS概略フロー_入出庫_生産_20250703VN.pdf`, khác tên yêu cầu một dấu chấm). Mã `wsc-50e045acef39dbcd38aff8fb`: 20 chunk, 14 chunk dùng được, 14 vector dày. Sổ cái `ready`, 1 lần thử. |
| F02 | Opcenter_Modelingの基本構造と生産履歴登録システムの変更点 1.pptx | Thiếu | Thư viện có `SRC-5595C2F7` (tên thực thiếu số `1`) nhưng mã `wsc-f5317d657bb48200fe0fa217` có 0 chunk, 0 vector. Sổ cái `failed` sau 8 lần thử, lỗi `source_text_unavailable`. |
| F03 | KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx | Thiếu | Thư viện có `SRC-07855C5B` nhưng mã `wsc-72b177b9dab655fc0371095f` có 0 chunk, 0 vector. Sổ cái `failed` sau 7 lần thử, lỗi `source_text_unavailable`. |
| F04 | KDC_P3MOM_MCO-309_コンポーネント設計.xlsx | Thiếu | Thư viện có `SRC-9EC673C5` nhưng mã `wsc-a6d76176e0998559e07f7072` có 0 chunk, 0 vector. Sổ cái `failed` sau 7 lần thử, lỗi `source_text_unavailable`. |
| F05 | 生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf | Thiếu | Thư viện có `SRC-4DEE4A6B` (ký tự `&` thành `_`) nhưng mã `wsc-51548ca220d6ccc9ec419c8c` có 0 chunk, 0 vector. Sổ cái `failed` sau 8 lần thử, lỗi `source_text_unavailable`. |
| F06 | MOMデータ連携説明_20251220.pdf | Thiếu | Thư viện có `SRC-9EB12A49` nhưng mã `wsc-015a1b6d9a94dc147ca10588` có 0 chunk, 0 vector. Sổ cái `failed` sau 8 lần thử, lỗi `source_text_unavailable`. |
| F07 | Lưu trình_lỗi phát sinh khi sản xuất AMS.txt | Thiếu | Quét toàn bộ 1284 bản ghi thư viện theo tên (`Lưu trình`, `Báo cáo`, `xuất kho`, `lỗi phát sinh`) được 0 bản ghi. Tệp chưa từng đưa vào thư viện. |
| F08 | Báo cáo lỗi xuất kho AMS.xlsx | Thiếu | Như F07, quét tên được 0 bản ghi. Tệp chưa từng đưa vào thư viện. |
| F09 | マテコン操作手順書_v001_生産技術 TV.pdf | Thiếu | Thư viện có 3 tên cùng họ (`_TV.pdf` là `SRC-B49372DD`, `_1.xlsx`, `_TV.xlsx`) nhưng cả 3 mã `wsc-*` đều 0 chunk, 0 vector. Sổ cái `failed` sau 8 lần thử, lỗi `source_text_unavailable`. Bản PDF yêu cầu chưa có vector. |
| F10 | MOMのRevUp手作業方法_20260324.pptx | Thiếu | Quét tên (`RevUp`, `20260324`, `手作業`) được 0 bản ghi trong thư viện. Từ `RevUp` xuất hiện trong 52 chunk của 6 nguồn khác nhưng đó là từ trong nội dung, không phải tệp gốc. |
| F11 | AMS_設計変更.pdf | Có | Thư viện có `SRC-551CC936`. Mã `wsc-b4f7ba061c5c7e3bb4b84eb3`: 32 chunk, 29 chunk dùng được, 29 vector dày. Sổ cái `ready`, 1 lần thử. |
| F12 | PLMシステム基礎講習_20250918 2.pptx | Thiếu | Quét tên (`20250918`, `基礎講習`) được 0 bản ghi. Từ `PLM` xuất hiện trong 8 nguồn khác nhưng đó là từ trong nội dung, không phải tệp gốc. |

## 4. Kết luận: MỚI MỘT PHẦN

Kho tài liệu MOM **mới ingest một phần** vào RAG v2 bằng BGE-M3.

Bằng chứng:

- Đúng mô hình BGE-M3 1024 chiều (`BAAI/bge-m3`, bản `5617a9f`, 2132 vector dày, blob 4096 byte), ingest gần nhất 2026-09-24 10:54:17 giờ UTC.
- Chỉ **2/12 tệp** có vector đầy đủ: F01 (14 vector) và F11 (29 vector), cả hai đều `ready` ngay lần thử đầu.
- **6/12 tệp** đã có trong thư viện nhưng ingest thất bại (`failed`, lỗi `source_text_unavailable`, thử 7-8 lần, 0 chunk): F02, F03, F04, F05, F06, F09.
- **4/12 tệp** chưa từng vào thư viện (quét tên 0 kết quả): F07, F08, F10, F12.

## 5. Việc thiếu và gợi ý ingest bổ sung

Số tệp thiếu vector: **10/12**.

Nhóm 1 — 6 tệp có trong thư viện nhưng lỗi `source_text_unavailable` (F02, F03, F04, F05, F06, F09): văn bản trích xuất không tới được khâu chuẩn bị. Gợi ý: mở từng tệp gốc trong `D:\Sandbox\MOM_QLLSSX_WMS`, trích xuất lại (PDF tiếng Nhật dùng OCR, XLSX đọc từng sheet có tên), nạp lại vào đúng sổ tay `MOM / Opcenter` rồi chạy lại chuẩn bị nguồn và kiểm tra sổ cái chuyển sang `ready` trước khi nhúng.

Nhóm 2 — 4 tệp chưa có trong thư viện (F07, F08, F10, F12): đưa tệp gốc vào sổ tay `MOM / Opcenter`, xác nhận xuất hiện trong `notebook_sources.jsonl` với trạng thái `ready`, rồi chạy ingest BGE-M3 trên CPU và đối chiếu mã `wsc-*` có chunk và vector như F01 và F11.

Kiểm tra lại sau ingest: đếm vector dày theo từng mã `wsc-*` phải lớn hơn 0, sổ cái không còn `failed` với lỗi `source_text_unavailable`, và thời gian `MAX(created_at)` trong `chunk_embeddings` phải mới hơn 2026-09-24.
