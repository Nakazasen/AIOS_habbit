# Báo cáo bổ sung ingest tài liệu MOM

Ngày: 2026-09-25
Nhánh: `phieu-viec/rag-fix1`
Không sửa `main`. Không đổi `BGE_BACKEND` và `AIOS_RAG_V2_SUMMARY_FIRST`. Không sửa logic pipeline.

## 1. Nguyên nhân gốc của `source_text_unavailable`

Lỗi này không phải lỗi trích xuất file.

Sáu file F02, F03, F04, F05, F06, F09 đã có văn bản trong thư viện trước khi điều tra:

| Mã | Bản ghi sổ tay | `content_text` | `extraction_status` | Sổ cái lúc đầu |
| --- | --- | ---: | --- | --- |
| F02 | `SRC-5595C2F7` | 2169 | ready | temporary `SRC-A3BE457A`, failed, 8 lần, `source_text_unavailable` |
| F03 | `SRC-07855C5B` | 27943 | ready | temporary `SRC-1C3F3EFE`, failed, 7 lần |
| F04 | `SRC-9EC673C5` | 13924 | ready | temporary `SRC-8AD9E669`, failed, 7 lần |
| F05 | `SRC-4DEE4A6B` | 14501 | ready | temporary `SRC-61762C1B`, failed, 8 lần |
| F06 | `SRC-9EB12A49` | 8221 | ready | temporary `SRC-4012CFFF`, failed, 8 lần |
| F09 | `SRC-B49372DD` | 46680 | ready | temporary `SRC-65713598`, failed, 8 lần, `wsc-2d528c22ed8a8466fba9c9bd` |

Bản tạm cùng nội dung cũng còn text. Ví dụ F05 temporary `SRC-61762C1B` còn 14501 ký tự, trạng thái `added_to_notebook`.

Chỗ gán lỗi là `_drain_preparation_queue` trong `workspace_chat_rag_v2_adapter.py`. Drain chỉ lấy text từ `_SOURCE_CACHE`, một dict trong RAM của tiến trình. Cache trống, hoặc text rỗng, thì ghi `failed` / `source_text_unavailable`. Drain không đọc lại `notebook_sources.jsonl` hay `temporary_sources.jsonl`.

Vì vậy file đã trích xuất xong vẫn fail sau khi tiến trình khởi động lại, hoặc khi drain nhận hàng từ sổ cái mà không nhận lại text. Không có flag hay config nào buộc drain đọc text đã lưu.

### Trích xuất thủ công

Cùng hàm `extract_text_chunks_from_file` mà khâu đọc file dùng.

- F05 `D:\Sandbox\MOM_QLLSSX_WMS\tailieugoc\生産履歴登録システム&着完工登録システム制作仕様_r2_2025-2-17 - 副本.pdf`: 56 chunk, 14446 ký tự, trạng thái `extracted`. Cảnh báo: thiếu `pdf_inspector`, đã rơi về PyMuPDF. Không phải `source_text_unavailable`.
- F03 `D:\Sandbox\MOM_QLLSSX_WMS\tailieugoc\仕様書\MOM\AMS以外のラインからの出庫指示\KDC_P3MOM_MCO-309_システムインターフェイス設計.xlsx`: 121 chunk, 59645 ký tự sheet, 97 chunk `extracted_partial`, 24 ảnh `unsupported_no_local_ocr` vì không có Tesseract (`AIOS_TESSERACT_CMD` trống, không có trên PATH). Sheet text vẫn có. Không phải lý do sổ cái fail.

## 2. Đã sửa gì

Không sửa code. Không sửa config. Sáu file này dừng ở đây, không ingest lại.

Đề xuất sửa logic, chưa làm: khi cache RAM không có text, drain phải nạp lại text từ bản ghi bền (`notebook_sources.jsonl` hoặc `temporary_sources.jsonl`) theo `source_scope` + `source_id` trước khi fail. Chỉ fail `source_text_unavailable` khi bản ghi bền cũng không có text. Không được xoá đường cũ.

Lúc kiểm tra lại, sáu dòng sổ cái temporary không còn `failed` / `source_text_unavailable`. Chúng đang `pending`, `last_error` rỗng, `attempt_count` 0. Việc này không do script bổ sung ghi. Một drain khác đang chạy đã xếp lại hàng. Vector của sáu mã này vẫn là 0.

## 3. Bốn file đã đưa vào sổ tay MOM / Opcenter

| Mã | File | Mã sổ tay | Ký tự |
| --- | --- | --- | ---: |
| F07 | Lưu trình_lỗi phát sinh khi sản xuất AMS.txt | `SRC-1C41F027` | 21043 |
| F08 | Báo cáo lỗi xuất kho AMS.xlsx | `SRC-69F104FA` | 4921 |
| F10 | MOMのRevUp手作業方法_20260324.pptx | `SRC-79B78BA2` | 1687 |
| F12 | PLMシステム基礎講習_20250918 2.pptx | `SRC-3D34DC0C` | 5457 |

Cả bốn nằm trong `local_cases/workspace_chat/notebook_sources.jsonl`, `notebook_id=mom_opcenter`. Sổ cái notebook của bốn mã này là `ready`, không có `source_text_unavailable`.

Index mà pipeline notebook dùng không phải file khảo sát cũ. `mom_opcenter` thuộc collection `tri_thuc`, `storage_root` trống, nên vector ghi vào:

`local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`

File khảo sát `bge_m3_hybrid/workspace_chat.sqlite` là index hồ sơ cũ. F01 và F11 vẫn nằm ở đó. Bốn file mới không được ghi vào file đó.

## 4. Bảng 12 file

Vector dày đếm trên chunk `retrievable=1`. Trước lấy từ khảo sát 2026-09-25 trên index hồ sơ cũ. Sau đếm trên index collection `tri_thuc`, là nơi ingest notebook ghi.

| Mã | `wsc-*` | Vector trước | Vector sau | Còn thiếu? |
| --- | --- | ---: | ---: | --- |
| F01 | `wsc-50e045acef39dbcd38aff8fb` | 14 | 14 trên index cũ, 0 trên collection | Không. Đã có từ trước, không ingest lại. |
| F02 | `wsc-f5317d657bb48200fe0fa217` | 0 | 0 | Có. Chưa sửa drain. |
| F03 | `wsc-72b177b9dab655fc0371095f` | 0 | 0 | Có. Chưa sửa drain. |
| F04 | `wsc-a6d76176e0998559e07f7072` | 0 | 0 | Có. Chưa sửa drain. |
| F05 | `wsc-51548ca220d6ccc9ec419c8c` | 0 | 0 | Có. Chưa sửa drain. |
| F06 | `wsc-015a1b6d9a94dc147ca10588` | 0 | 0 | Có. Chưa sửa drain. |
| F07 | `wsc-1e085174af345d01afbf88d6` | 0 | 78 | Không. `created_at` mới nhất `2026-09-25T04:08:21Z`. |
| F08 | `wsc-6349bfab87ce7a5eb246e10f` | 0 | 9 | Không. `2026-09-25T04:12:16Z`. Index cũ có 9 vector từ `2026-09-16`, không tính là lần này. |
| F09 | `wsc-2d528c22ed8a8466fba9c9bd` | 0 | 0 | Có. Chưa sửa drain. |
| F10 | `wsc-d320e16fa80ee7e311b42fb7` | 0 | 3 | Không. `2026-09-25T04:13:12Z`. |
| F11 | `wsc-b4f7ba061c5c7e3bb4b84eb3` | 29 | 29 trên index cũ, 0 trên collection | Không. Đã có từ trước, không ingest lại. |
| F12 | `wsc-e9d27b6c728c286f2cf0ef93` | 0 | 10 | Không. `2026-09-25T04:17:54Z`. |

`MAX(created_at)` trên collection `tri_thuc`: `2026-09-25T04:17:54.738143+00:00`, mới hơn 2026-09-24.
`MAX(created_at)` trên index hồ sơ cũ vẫn `2026-09-24T10:54:17.861641+00:00`, vì bốn file mới không ghi vào đó.

## 5. File vẫn thiếu

F02, F03, F04, F05, F06, F09 vẫn 0 vector. Text đã có trong sổ tay. Không ingest lại vì lỗi nằm ở drain chỉ đọc cache RAM. Cần sửa logic như mục 2 rồi mới chạy lại.
