# Vé `stale-check` — Đếm document stale thực tế (chỉ đọc)

- Ngày: 2026-09-29 (~23:0x +07), máy `h410asrock` (OMP).
- Nhánh: `phieu-viec/rag-fix1`. Vé chỉ đọc: không ghi index, không embed, không sửa code, không đụng ổ D.
- Nguồn đọc: bản copy index production trên C — `C:\AIOS_p1_4\tri_thuc\library.sqlite`,
  mở bằng `file:…?mode=ro` (không ghi).

## 1. Kiểm chứng bản copy đúng là index production

| Mục | Giá trị |
| --- | --- |
| Nguồn gốc bản copy (theo `C:/AIOS_p1_4/out/copy_manifest.json`) | `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` (2.552.659.968 byte) |
| SHA-256 nguồn = đích = giá trị ghim P1.3 | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` (`src_matches_expected: true`, `copy_matches_src: true`) |
| SHA-256 bản copy C **đo lại trong vé này** (23:xx) | `062ec090…` — không đổi; 2.552.659.968 byte |
| Index production trên D lúc 22:31 (+07) | Cùng SHA `062ec090…`, mtime nguyên — đã kiểm ở vé E2 vòng 4 (commit `fe409e9`) |

→ Bản copy C chính là index production, còn nguyên giá trị; vé này **không** đọc/ghi gì trên ổ D.

## 2. Định nghĩa "thiếu embedding ONNX" (khớp semantics repo)

Chunk `retrievable=1` bị coi là **thiếu** khi: không có row cùng `chunk_id` với
`model_fingerprint` ONNX (`016c5255…`) trong `chunk_embeddings` / `chunk_sparse_embeddings`,
**hoặc** có row nhưng `content_hash` ≠ `sha256(text)`.

Đúng theo `src/aios_habit/rag_v2/index.py` (`_ensure_embeddings`, dòng 1342–1351) và
`scripts/migrate_vectors_to_onnx.py` (`plan_migration`, `_row_needs_migration`).
Script đếm chạy cục bộ (không commit): `C:/AIOS_p1_4/out/stale_check/stale_check.py`;
kết quả thô JSON: `C:/AIOS_p1_4/out/stale_check/stale_check_result.json`.

## 3. Số liệu đo được

| Chỉ tiêu | Số |
| --- | --- |
| Tổng số document trong index | **496** |
| Tổng số chunk | 133.144 |
| Chunk `retrievable=1` | **107.331** |
| Chunk `retrievable=0` (không cần embed) | **25.813** |
| Chunk `retrievable=1` **thiếu dense ONNX** | **0** (0 thiếu row, 0 hash lệch) |
| Chunk `retrievable=1` **thiếu sparse ONNX** | **0** (0 thiếu row, 0 hash lệch) |
| **Document có ≥1 chunk thiếu dense hoặc sparse ONNX** (`retrievable=1`) | **0 / 496** |

Kết luận: **KHÔNG còn document stale cần embed lại.** Toàn bộ 107.331 chunk truy hồi được
đều đã có đủ vector dense + sparse ONNX với `content_hash` khớp nội dung hiện tại.

## 4. Đối chiếu fingerprint vector với `016c5255…`

| Bảng | Fingerprint | Số row |
| --- | --- | --- |
| `chunk_embeddings` (dense) | `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb` | **107.331** (đúng bằng số chunk retrievable) |
| `chunk_embeddings` (dense) | `ce7fb53f797f0973e2cbf51d6a6ffef4de9a32b659b979f45663c6c360c8e43c` (PyTorch cũ) | 340 |
| `chunk_sparse_embeddings` (sparse) | `016c5255…` | **107.331** |
| `chunk_sparse_embeddings` (sparse) | `ce7fb53f…` (PyTorch cũ) | 340 |
| `chunk_multivector_embeddings` | — | 0 row |

- Fingerprint hiện hành của vector **khớp đúng** `016c5255…` (ONNX fp32 BGE-M3), đủ trên
  cả 107.331 chunk truy hồi được, cả dense lẫn sparse.
- 340 row PyTorch cũ là **dead weight vô hại**: cả 340 đều trùng `chunk_id` 100% với bản ONNX
  (đã kiểm chéo: `pytorch_rows_with_onnx_dup = 340/340`), mọi truy vấn lọc theo fingerprint
  nên không ảnh hưởng — khớp ghi nhận trước ở `p2-b8-bao-cao-nghiem-thu.md`.

## 5. Kiểm chứng chéo (độ tin cậy của con số)

- Vòng quét đọc đúng **107.331/107.331** chunk `retrievable=1` (`scanned_ok: true`).
- Số "thiếu row" tính bằng hai cách độc lập (SQL thuần `LEFT JOIN … IS NULL` và vòng quét
  Python) **trùng khớp**: dense 0, sparse 0.
- Tổng "thiếu" = thiếu row + hash lệch, tự nhất quán (`cross_check_dense/sparse: true`).
- Mọi 496/496 document đều có ít nhất 1 chunk `retrievable=1`; không document nào chỉ có
  chunk `retrievable=0` → con số document-stale không bị che bởi document rỗng.
- Truy vấn chỉ chạy `mode=ro`; không ghi index, không tạo journal, không embed, không gọi
  provider/mạng ngoài, không dùng `functions.find`. Thời gian chạy: 8,4 giây.

## 6. Liên hệ với con số "422/496" cũ

Số **422/496** xuất hiện ở vé E2 là loại stale **khác**: document có tệp nguồn
`file_changed_since_ingest` (đổi sau khi nhập) → cần **nhập lại**, không phải thiếu vector.
Số đó do tiền kiểm E2 tính bằng so fingerprint tệp nguồn; vé này không đo lại vì lệnh cấm
đụng ổ D (nơi chứa tệp nguồn). Còn "stale cần embed lại" — câu hỏi của vé — đo được là **0**.

Từ đó: 74/496 document được E2 dùng để truy vấn là các document *nguồn còn mới*; còn
trạng thái vector của index đã đầy đủ ONNX.
