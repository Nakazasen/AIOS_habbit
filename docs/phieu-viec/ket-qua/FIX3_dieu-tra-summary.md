# Điều tra: overview abstain vì `no_document_summaries`

Ngày: 2026-09-25
Nhánh: `phieu-viec/rag-fix1`
Chỉ đọc code và index. Không sửa code. Không viết summary tay cho file MOM.

Index đo: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`, chế độ chỉ đọc.
Index cũ để đối chiếu: `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/workspace_chat.sqlite`.

## 1. Summary được sinh ở đâu, và khi nào không sinh

Điểm sinh nằm trong `StructureAwareChunker.chunk_elements`, `src/aios_habit/rag_v2/chunking.py` dòng 153–157.

Điều kiện duy nhất để gọi builder: có chunk thân, và `len(usable_elements) >= 3`. Không có ngưỡng độ dài ký tự. Không có cờ bật tắt. Phần tử `FAILED` / `UNSUPPORTED` không tính. Không có `try/except` nuốt lỗi ở chỗ này: không đủ 3 phần tử thì không tạo, không ghi warning.

`_build_document_summary` (dòng 294–333) chỉ lấy heading và text:

- Heading: `element_type == HEADING`.
- Thân: tối đa 1500 ký tự từ phần tử `TEXT`, theo thứ tự phần tử, không phải bản tóm tắt sinh bởi model.
- Không heading và không text thì trả `None` dù đã qua ngưỡng 3 phần tử.
- Chunk summary đặt `file_type="document_summary"`, `chunk_id="{document_id}-summary"`.
- Không gán `privacy_labels` và không gán `source_fingerprint`. Hai trường này để mặc định rỗng / null.

Workspace Chat không đưa file gốc vào chunker. `_materialize_sources` (`workspace_chat_rag_v2_adapter.py` dòng 2169–2170) ghi toàn bộ text đã trích thành một file `.txt`. `TextDocumentConverterAdapter.convert` (`converters.py` dòng 88–89) tách phần tử bằng dòng trống `\n\n`. Một file PDF/PPTX/XLSX nhiều trang, sau khi đã dồn thành một khối text ít đoạn, chỉ còn 1–2 phần tử. Cổng `>= 3` không bao giờ mở.

## 2. Mười hai file MOM trong `tri_thuc`

Đếm trực tiếp theo `document_id` của text sổ tay:

| Mã | Chunk summary | Chunk thân `txt` | Đoạn trống-dòng của file materialized |
| --- | ---: | ---: | --- |
| F01 | 1 | 19 | 7 |
| F02 | 0 | 4 | 2 |
| F03 | 1 | 49 | không đo lại; đã có summary |
| F04 | 1 | 28 | không đo lại; đã có summary |
| F05 | 1 | 58 | không đo lại; đã có summary |
| F06 | 1 | 31 | không đo lại; đã có summary |
| F07 | 1 | 78 | 76 |
| F08 | 1 | 10 | không đo lại; đã có summary |
| F09 | 1 | 110 | không đo lại; đã có summary |
| F10 | 0 | 4 | 2 |
| F11 | 1 | 31 | không đo lại; đã có summary |
| F12 | 1 | 13 | không đo lại; đã có summary |

F02 và F10 thiếu summary vì file materialized chỉ có 2 đoạn tách bằng dòng trống, dưới ngưỡng 3 phần tử. Không phải vì loại pptx bị cấm, và không phải vì lỗi bị nuốt.

Mười summary hiện có đều dài 1551 ký tự, dạng tiền tố chứ không phải tóm tắt:

- Khung cố định tiếng Anh: `[DOCUMENT ARCHITECTURE & SUMMARY]` rồi `## INTRODUCTION`.
- Không có mục lục. Text sổ tay không có dòng bắt đầu bằng `#`, nên không có heading.
- Thân là 1500 ký tự đầu của các phần tử `TEXT`: tiếng Nhật (F03, F04, F05, F06, F11), tiếng Việt trộn Nhật (F01, F09), tiếng Việt (F07, F08), và XML thô của slide (F12, bắt đầu `<p:sld xmlns=`).
- Chất lượng: đủ để biết file bắt đầu bằng cái gì. Không đủ để trả lời câu hỏi quy trình. F12 là rác XML.

Cả 10 summary có `source_fingerprint` null và `privacy_labels_json` = `[]`. Chunk thân cùng document thì có fingerprint khớp file materialized và nhãn `cloud_safe`.

Index cũ lúc đo này: 32 chunk `document_summary` retrievable, 101 document. Cũng 32/32 summary thiếu fingerprint và privacy. Con số 28/93 trong khảo sát trước là mốc cũ hơn, không phải một cơ chế khác.

## 3. Đường tìm summary của overview

`search_summaries_with_summary` (`index.py` dòng 2874–2887) là lexical thuần. Docstring ghi không embed, không quét chunk thân. SQL chỉ lấy `file_type='document_summary'`. Điểm là `_score_candidate`. Hàng không có điểm lexical vẫn được giữ với điểm 0.01, nhưng chỉ sau khi qua bộ lọc.

Bộ lọc làm rơi cả 10 summary trước khi chấm điểm:

- `pipeline.py` dòng 542–545 đặt `allowed_privacy_labels` gồm `cloud_safe` và các nhãn chuẩn.
- `_privacy_is_allowed` (`index.py` dòng 3488) trả false nếu danh sách nhãn rỗng.
- Query production gửi `expected_source_fingerprints` bằng hash file materialized.
- `_is_stale` (dòng 3493–3494) coi fingerprint null là khác hash đó, nên stale.

Một trong hai lọc là đủ để `eligible` rỗng. Hàm trả `no_document_summaries` (dòng 2903). Đó đúng lý do 5 câu A abstain. Không phải vì từ khóa trượt.

Thử lexical trên 10 summary, bỏ qua lọc, với từ của 5 câu A:

- A1, A2, A5: 10/10 summary có ít nhất một token. Nhiều hit chỉ là `ra`, `và`.
- A3, A4: 4/10. Bốn summary tiếng Nhật gần như không chứa từ Việt của câu hỏi.
- Không có summary nào chứa cụm quy trình của câu hỏi. Khớp là token ngắn, không phải cùng ngôn ngữ hay cùng việc đang hỏi.

Sau khi sửa lọc, đường lexical vẫn xếp hạng yếu trên tài liệu Nhật. Đó là vấn đề chất lượng, không phải nguyên nhân abstain lần này.

## 4. Đề xuất sửa ở tầng pipeline

Không viết summary cho 12 file. Không chỉnh từ khóa cho 5 câu mẫu. Không đụng `detect_retrieval_mode` trong đề xuất này.

1. Khi tạo summary, chép `privacy_labels` và `source_fingerprint` từ phần tử hoặc chunk thân cùng document. Áp cho mọi ingest sau này, mọi collection. Không đổi nội dung summary.
2. Bỏ cổng cứng `usable_elements >= 3`, hoặc hạ thành “có ít nhất một phần tử TEXT/HEADING không rỗng”. Một tài liệu một đoạn vẫn được một summary tiền tố 1500 ký tự, cùng hàm hiện có. F02/F10 và mọi file materialized ít đoạn trống sẽ có summary. Không riêng MOM.
3. Backfill provenance, không backfill chữ: với mọi `document_summary` đang null fingerprint hoặc privacy rỗng, chép hai trường từ chunk thân cùng `document_id` nếu chunk thân có giá trị. Chạy một lần cho index đã có, kể cả index cũ 32 summary. Không sinh câu mới.
4. Sau khi (1)–(3) xong, nếu vẫn cần xếp hạng tốt hơn lexical: chấm summary bằng điểm lexical hiện có cộng cosine của embedding summary đã có, cùng ngưỡng fail-closed đang dùng cho dense. Không embed lại cả thân. Không thêm từ đồng nghĩa cho câu mẫu.

Phạm vi: `chunking.py` cho (1)(2), một lệnh bảo trì index cho (3), `search_summaries_with_summary` cho (4). Caller của chunker không đổi chữ ký. Flag `AIOS_RAG_V2_SUMMARY_FIRST` giữ tắt. Đường hybrid đầy đủ không đổi. Collection khác dùng cùng chunker sẽ hết lỗi lọc này ở lần ingest kế.

Kiểm tra sau khi được duyệt, không làm trong phiếu này: ingest một file txt một đoạn và một file nhiều đoạn vào index tạm, assert summary có fingerprint và privacy của chunk thân, rồi query overview với `allowed_privacy_labels` và fingerprint kỳ vọng phải trả summary đó. Câu held-out không lấy từ 10 câu mẫu.
