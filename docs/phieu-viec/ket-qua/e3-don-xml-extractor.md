# Vé E3 — Dọn XML thô ở extractor

Ngày chạy: 2026-09-30. Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Mã nguồn: `58c4b67` (fix + test); trạng thái vé: xem `docs/phieu-viec/mailbox/trang-thai.md`.

## 1. Rà soát 3 file — chỗ lọt tag XML thô

| File | Lọt XML thô? | Bằng chứng |
|---|---|---|
| `src/aios_habit/document_extractors.py` | **CÓ** | `_extract_xml_text` (nhánh regex khi cờ tắt) nhặt nội dung giữa các thẻ có chữ `t` nên kéo theo `]]>` của CDATA và bỏ sót văn bản anh em; `_clean_lines` chỉ bỏ thẻ dài ≤ 160 ký tự trên một dòng; `normalize_extracted_text` khi cờ tắt không dọn gì; và bộ dọn `_strip_xml_markup` (khi cờ bật) bỏ sót thẻ trải nhiều dòng, attribute chứa `>` trong nháy, và DOCTYPE nội bộ |
| `src/aios_habit/excel_extractors.py` | **KHÔNG** | Các đường sinh chuỗi: `normalize_cell_value` (giá trị ô), `_chart_title`, `_chart_series`, `_anchor`, `_LegacyMerge.__str__` — chỉ trả chuỗi/biểu đồ, không tự phân tích hay sinh XML; phần XML của workbook do `document_extractors` đọc (đã nằm trong phạm vi fix) |
| `src/aios_habit/deep_document_parsers.py` | **KHÔNG** | `run_docling` / `run_marker` chỉ chạy thư viện ngoài và trả markdown; không có mã nào cắt hay gắn markup. Khi cờ bật, kết quả vẫn đi qua `normalize_extracted_text` như các extractor khác |

Lưu ý luật: fix nằm sau cờ `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP`, **mặc định TẮT** —
mặc định vẫn giữ hành vi cũ (vẫn lọt) theo quy ước "flag mặc định giữ hành vi cũ".
Đường mặc định chứng minh không đổi: khi cờ tắt, `_strip_xml_markup` không được gọi lần nào (đếm bằng spy, 0 lần).

## 2. Fix

File `src/aios_habit/document_extractors.py`, bộ dọn `_strip_xml_markup` / `_XML_MARKUP_RE`:

1. Thẻ có attribute dạng `tên="giá trị"`: giá trị trong nháy được phép chứa `>` (hợp lệ theo XML) và XML xuống dòng giữa các attribute — nay được khớp và xoá trọn thẻ, không để lại `a:t`, `id="x"` hay `>` mồ côi.
2. `<!DOCTYPE ... [ ... ]>` có tập con nội bộ — nay xoá trọn, không để lại `]>`.
3. Cho phép xuống dòng giữa marker thay thế namespace và dấu `>` đóng thẻ.

Giữ nguyên hành vi đã duyệt: giải mã entity trước khi bỏ thẻ (`&amp;`, `&eacute;`, `&#253;`), giữ nội dung trong CDATA, giữ dữ kiện khi thẻ bị cắt cụt (`<a:t` thiếu `>` vẫn giữ phần chữ sau).

Đo trước/sau trên đúng các ca đã dựng (cùng một hàm, cùng input):

| Đầu vào | Trước fix | Sau fix |
|---|---|---|
| `<a:t\n  id="x"\n>text</a:t>` | ` a:t\n  id="x"\n>text ` | `text` |
| `<a:t foo="a>b">text</a:t>` | ` b">text ` | `text` |
| `<!DOCTYPE a [ <!ENTITY x "y"> ]>real text` | `  ]>real text` | `real text` |
| PPTX có XML truncated nhiều dòng, chạy end-to-end, cờ bật | `Slide text:\np:sld PART-402 nvarchar(4000) 0 1` | `Slide text:\nPART-402 nvarchar(4000) 0 1` |

Bộ dọn vẫn idempotent (dọn hai lần ra cùng kết quả) và giữ dữ kiện (`PART-402`, `nvarchar(4000)`, `0 1`); văn bản nhiễu 200.000 ký tự xử lý trong 0,030 giây.

## 3. Test

| Test | Kịch bản | Kết quả |
|---|---|---|
| `test_xml_cleanup_handles_nested_cdata_entities_and_multiline_tags` | XML lồng nhau; CDATA (có và không có chữ giống thẻ); entity `&eacute;`, `&amp;`, `&#253;`, `&lt;`; thẻ nhiều dòng; attribute chứa `>`; DOCTYPE nội bộ; idempotent | pass |
| `test_pptx_xml_cleanup_strips_pretty_printed_truncated_markup` | PPTX có XML truncated nhiều dòng (rơi nhánh dọn dự phòng) — sạch `xmlns`, `p:sld`, `<p:`, `</`, `a:t`, `<?xml` | pass |
| `test_excel_drawing_xml_cleanup_strips_truncated_multiline_markup` | XLSX có drawing XML truncated nhiều dòng — chữ trong hình vẽ sạch `xmlns`, `xdr:`, `a:t`, `<?xml`, `<xdr` | pass |
| `test_old_file_reimport_still_skipped_when_xml_cleanup_enabled` | Luật "vất lại file cũ thì bỏ qua" khi cờ dọn bật: nhập lại đúng file `.pptx` cũ → `already_imported`, không trích xuất lại (đếm 1 lần gọi), văn bản đã trích sạch `xmlns` / `<a:t>` | pass |

- Kiểm chứng đỏ-trước-xanh-sau: tạm trả mã nguồn về bản trước fix → **3 test XML đỏ** (`test_xml_cleanup_handles_nested_cdata_entities_and_multiline_tags` báo thừa `a:t`, `id="x"`, `>`; `test_pptx_xml_cleanup_strips_pretty_printed_truncated_markup` báo còn `p:sld`; `test_excel_drawing_xml_cleanup_strips_truncated_multiline_markup` báo còn `xdr:wsDr`); khôi phục fix → 30 bài của tệp test trích xuất xanh, tệp mã nguồn khớp `HEAD`.
- Test liên quan: `pytest -q tests/test_document_extractors.py tests/test_workspace_chat_folder_import.py` → **58 đạt, 0 lỗi**; thêm `tests/test_workspace_chat_source_ingest.py` (đường trích xuất của chat) → **73 đạt, 0 lỗi** (extractor 30, nhập thư mục 28, ingest nguồn 15).
- Cổng đầy đủ trên máy này (Python `3.11.14`):
  - `uv run --no-sync --group dev python -m compileall -q src tests` → không lỗi.
  - `PYTHONPATH=src uv run --no-sync --group dev python -m aios_habit.cli audit` → `"status": "PASS"`, không lỗi, không cảnh báo.
  - `PYTHONPATH=src uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → `IMPORT_OK`.
  - `pytest -q` toàn bộ (thêm `PYTHONPATH` trỏ `xlrd` tạm, xem mục 5): **3.262 đạt, 3 bỏ qua, 37 lỗi, 10 error** trong 248,51 giây. Không bài nào đỏ nằm ở vùng fix (extractor, nhập thư mục chat, ingest nguồn, converter).
  - Đối chứng A/B trên đúng cây đó, chỉ lùi `document_extractors.py` về bản trước fix: **3.259 đạt, 3 bỏ qua, 40 lỗi, 10 error**; so từng bài thì **đúng 3 test XML mới chuyển đỏ**, không thêm/bớt bài nào khác — tức 37 lỗi + 10 error còn lại là có sẵn ở `HEAD`, không do fix.

## 4. Ràng buộc vé

- Không ghi index, không embed, không `--apply`: chỉ sửa mã + test + tài liệu.
- Không merge `main`.
- Không ghi ổ D: mọi tệp tạm của test/tiện ích nằm trên ổ C (`%TEMP%` của tiến trình, `C:/tmp/e3-py311` cho `xlrd`); thay đổi trên ổ D chỉ là tệp mã/test/tài liệu trong repo.
- Flag rollback: `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP` (giá trị mặc định: TẮT — giữ hành vi cũ).

## 5. Điểm khác vé, môi trường, đề xuất

- Vé yêu cầu "viết hàm dọn XML": hàm dọn đã có từ vé E3 vòng trước (`_strip_xml_markup`); vòng này siết 3 lỗ hổng đã chứng minh ở mục 2 và bổ sung test theo đúng yêu cầu (lồng nhau, CDATA, entity, luật file cũ) nên không tạo hàm trùng.
- Đường mặc định (cờ tắt) vẫn lọt XML như thiết kế cũ. Muốn dọn ở đường mặc định cần vé riêng (đổi mặc định = đổi hành vi extractor; kèm đo trước/sau và tính chuyện ingest lại) — vé này cấm ghi index nên không làm.
- Môi trường 1: nhóm `dev` thiếu `xlrd` (nằm trong extra `rag-ingestion-xls`) nên lần chạy suite đầu dừng ở khâu thu thập test; đã cài đúng bản khoá `xlrd 2.0.2` vào `C:/tmp/e3-py311` (theo tiền lệ vé 0.3) rồi chạy lại. Không sửa khai báo phụ thuộc của dự án.
- Môi trường 2: 37 lỗi + 10 error còn lại của suite là **có sẵn ở `HEAD`** (đối chứng A/B ở mục 3). Nhóm chính: thiếu gói `graphifyy` (10 bài), tiến trình BGE/ONNX worker (9 bài), `uv.lock` và đóng gói (4 bài), `test_error_cases_f4` thiếu tệp dữ liệu Linux `/home/hatch/...` (10 error), nhóm workspace-chat (reconcile/owner-flow/i18n copy), vài bài eval/mom pilot, và 2 tệp trong `tests/fixtures/` bị thu thập như test. Vé này không đụng các vùng đó.
- Ngữ cảnh máy (không áp dụng): máy còn stash cũ `OMP-stash-truoc-P1.2-2026-09-28` (việc dở của phiên trước, có sửa `workspace_chat_*.py`); chưa xác minh liên quan tới nhóm lỗi workspace-chat. Stash được giữ nguyên, không áp vào cây vé này.
- Sự cố thao tác (minh bạch): khi kiểm chứng đỏ-xanh, một lệnh `git stash pop` đã áp nhầm stash cũ nói trên làm cây tạm bẩn trong ít phút; đã khôi phục đúng `HEAD` cho toàn bộ tệp bị áp, stash còn nguyên trong danh sách (không mất). Hai lần chạy suite ở mục 3 đều chạy trên cây sạch: lần có fix trước, lần lùi fix sau (đổi duy nhất tệp `document_extractors.py` trong lúc chạy).
- Đề xuất (ngoài phạm vi vé): (1) vé riêng bật dọn XML mặc định + đo lại chunk bẩn + tính ingest lại; (2) vé riêng xử lý phần việc dở của nhánh (stash P1.2, nhóm lỗi workspace-chat) để suite về mức như báo cáo cũ.
