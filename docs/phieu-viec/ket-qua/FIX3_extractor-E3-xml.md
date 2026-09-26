# Phiếu việc E3 — Dọn XML thô ở bộ trích xuất

Ngày chạy: 2026-09-26. Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Mã nguồn và kiểm thử: `40b2a04` (commit cục bộ, chưa đẩy).

## Kết luận

- Điểm rò rỉ nằm ở `src/aios_habit/document_extractors.py::_extract_xml_text`: biểu thức chính quy tìm thẻ có chữ `t` ở bất kỳ vị trí nào, kể cả trong thuộc tính đường dẫn không gian tên. Nội dung XML lồng bị bắt như văn bản; `_clean_lines` chỉ bỏ thẻ ngắn tối đa 160 ký tự nên thẻ thuộc tính dài và mảnh thẻ ở ranh giới đoạn còn lọt vào kết quả.
- Đã thêm cờ `AIOS_DOCUMENT_EXTRACTOR_XML_CLEANUP`, mặc định tắt. Khi bật, PPTX và chữ trong hình vẽ Excel được đọc bằng `ElementTree`; văn bản nút và phần đuôi được giữ. Với đoạn trộn hoặc XML không phân tích được, bộ chuẩn hóa bỏ dấu thẻ, thuộc tính không gian tên và dấu phân cách chú thích/hướng dẫn nhưng giữ nội dung bên trong để không nuốt dữ kiện. XML hợp lệ loại nút chú thích khi trích xuất. Khi cờ tắt, đường đọc cũ giữ nguyên.
- Các kiểm thử xác nhận cờ mặc định tắt; dọn mảnh `xmlns`/`<p:sld` bị cắt; giữ mã `PART-402`, kiểu `nvarchar(4000)`, số `0`, `1` kể cả khi nằm cạnh thẻ, chú thích hoặc chỉ dẫn xử lý sai định dạng; XML hợp lệ loại nút chú thích; PPTX sạch tạo đoạn giống hệt khi cờ bật và tắt.

## Đo trước và sau

Đọc chỉ mục thử SQLite bằng `mode=ro`, bật `query_only`, lấy 1.272 đoạn vào bộ nhớ. Chỉ áp bộ chuẩn hóa mới trên bản sao trong RAM; không chạy trích xuất lại nguồn, nạp dữ liệu hoặc ghi chỉ mục. Vì vậy số đo dưới đây mô tả hiệu quả dọn nội dung chỉ mục thử hiện có, không phải kết quả di trú chỉ mục.

| Dấu hiệu trong đoạn | Trước | Sau |
|---|---:|---:|
| Có `xmlns` | 67 | 0 |
| Có `<p:sld` | 42 | 0 |
| Có thẻ XML | 79 | 0 |

Kiểm tra tìm từ khóa trên bản sao trước/sau, xếp theo `bm25` với 100 kết quả đầu:

| Dữ kiện đáp án đã biết | Hạng trước | Hạng sau |
|---|---:|---:|
| B1 — `11922` | 1 | 1 |
| B3 — `nvarchar(4000)` | 1 | 1 |
| B5 — `HOUSE_METHOD` | 1 | 1 |

`PRAGMA integrity_check` trả `ok`; kích thước tệp và thời điểm sửa chỉ mục giữ nguyên trước/sau. Chỉ mục thật không bị ghi.

## Kiểm tra

- Python: `3.11.14`.
- `uv run --no-sync --group dev python -m pytest -q tests/test_document_extractors.py`: **27 bài đạt**.
- `uv run --no-sync --group dev python -m compileall src tests`: hoàn tất, không báo lỗi biên dịch.
- `PYTHONPATH=src uv run --no-sync --group dev python -m aios_habit.cli audit`: `status=PASS`, không lỗi hoặc cảnh báo.
- `PYTHONPATH=src uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app; print('IMPORT_OK')"`: `IMPORT_OK`.
- `uv run --no-sync --group dev pytest -q`: **3.134 bài đạt, 2 bỏ qua, 23 lỗi**. Chín lỗi ở tiến trình BGE báo `bge_worker_init_stdout_eof`; chín lỗi ở bộ kết nối Graphify do thiếu `graphifyy==0.9.50`; hai kiểm thử đóng gói và hai kiểm thử `owner-workflow` không nạp được `aios_habit` trong tiến trình con; một kiểm thử báo `uv.lock` chưa khớp khai báo phụ thuộc. Không sửa khóa phụ thuộc, cài thêm gói hay tắt kiểm thử để lấy PASS.
- `git diff --check`: không có lỗi khoảng trắng sau khi cập nhật mã, kiểm thử và tài liệu.

## Bàn giao và giới hạn

- Mã nguồn và kiểm thử đã commit cục bộ: `6079808398c622a66c9f8184b1f5908ad4d1b4f3` và `40b2a04`.
- Chưa đẩy commit mã: `AGENT_RULES.md` mục 2 cấm đẩy thay đổi mã khi toàn bộ `pytest -q` chưa đạt. Trạng thái mailbox giữ `dang-lam`; không ghi `xong-cho-duyet`.
- Không ghi chỉ mục thật. Chỉ mục đang có vẫn giữ dữ liệu cũ; nếu cần làm sạch dữ liệu đã nạp, phải có phiếu riêng, chạy thử không ghi, sao lưu và được duyệt rõ ràng trước khi ghi.
