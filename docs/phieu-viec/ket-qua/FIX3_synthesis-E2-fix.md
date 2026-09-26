# Phiếu việc E2 — Sửa tổng hợp RAG và xác minh B1/B2/B3/B5

Ngày chạy: 2026-09-26. Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Mã nguồn đã kiểm tra: `a83f8ff4862283522aa5418e1d1233bcb9118ef9`.

## Kết luận

- Chế độ `full` ưu tiên các đoạn thân tài liệu khi truy xuất và tổng hợp; các đoạn tóm tắt được giữ phía sau làm ngữ cảnh bổ sung. Chế độ `overview` vẫn chỉ dùng đoạn tóm tắt.
- Thu hồi ứng viên có nhánh tìm định danh chính xác ngoài cửa sổ FTS; khi truy vấn có nhiều định danh, định danh cuối được ưu tiên cả lúc cứu ứng viên lẫn lúc xếp hạng.
- Bộ tổng hợp giữ đoạn có mã, số, kiểu dữ liệu và giá trị nằm sâu trong mảnh nguồn; cửa sổ đoạn có giới hạn, trích dẫn vẫn gắn với mảnh nguồn. Dấu ngoặc kép cong được ghép đúng cặp.
- B1, B2, B3 và B5 chạy bằng ONNX ở chế độ chỉ đọc. Mọi giá trị kiểm tra đều xuất hiện trong câu trả lời và trong bằng chứng mà trích dẫn dẫn tới. B4 bị loại khỏi chấm điểm theo yêu cầu.
- Không nạp dữ liệu, không chạy `--apply`, không ghi chỉ mục.

## Thay đổi

- `src/aios_habit/rag_v2/index.py`: trích định danh từ truy vấn, bổ sung tối đa 8 ứng viên khớp chính xác sau cửa sổ FTS; xếp định danh cuối cao hơn mã bảng tổng quát. Ở chế độ `full`, đoạn tóm tắt nối sau kết quả thân; `overview` tiếp tục chỉ trả đoạn tóm tắt.
- `src/aios_habit/rag_v2/pipeline.py` và `src/aios_habit/rag_v2/synthesis.py`: truyền ưu tiên đoạn thân vào tổng hợp cục bộ/nhà cung cấp khi tra cứu chi tiết; chấm điểm mã và giá trị chính xác; giữ cửa sổ bằng chứng có giới hạn và ghép giá trị bổ sung chỉ từ cùng mảnh nguồn được trích dẫn.
- Không thêm cờ cấu hình hay bí danh giao diện lập trình mới.

## Xác minh ONNX chỉ đọc

- Cấu hình: `BGE_BACKEND=onnx`, `AIOS_RAG_V2_SUMMARY_FIRST=1`, `AIOS_RAG_V2_SUMMARY_PROVENANCE=1`, `index_read_only=True`, `ensure_embeddings_on_open=False`.
- Phạm vi chỉ mục: 74 tài liệu, 1.272 đoạn, 1.064 đoạn truy xuất được.
- Kích thước trước và sau truy vấn: 29.851.648 byte; bằng nhau. Không có nạp dữ liệu hoặc cập nhật vector.
- B1: trước sửa, câu trả lời bỏ các mã dù chúng có trong bằng chứng; sau sửa, đủ ba mã kiểm tra và trích dẫn của từng mã dẫn tới bằng chứng chứa mã đó.
- B2: cả hai tên tệp thực thi đều xuất hiện và từng tên có trích dẫn hỗ trợ. Tuy nhiên, câu trả lời không gắn rõ tên dành cho ACR; không tính phép gán ACR/CTU là đã đạt. Kết quả này cũng đã được ghi nhận ở mức chuẩn D3.
- B3: trước sửa, câu trả lời bỏ kiểu/giới hạn có trong bằng chứng; sau sửa, đủ kiểu dữ liệu và độ dài kiểm tra, trích dẫn khớp bằng chứng.
- B5: trước sửa, đoạn định nghĩa bị rơi ngoài 100 ứng viên từ vựng; sau sửa, định danh trường, hai giá trị và ý nghĩa đều có trong câu trả lời, mỗi mục được trích dẫn hỗ trợ.

Lượt chạy kiểm tra đáp án không in nội dung mảnh nguồn hoặc câu trả lời đầy đủ. Toàn văn dữ liệu nguồn không được đưa vào báo cáo hay Git.

## Kiểm thử và cổng

- Python: `3.11.14`.
- Kiểm thử RAG liên quan và kiểm tra mã hóa cứng: 79 bài đạt.
- `uv run --no-sync --group dev python -m compileall src tests`: đạt.
- Lệnh kiểm tra CLI `audit` chạy từ thư mục gốc với `PYTHONPATH=src`: `status=PASS`, không lỗi/cảnh báo.
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` chạy từ `src`: đạt.
- `git diff --check` và `git diff --cached --check`: đạt, không có lỗi khoảng trắng trước khi ghi nhận mã nguồn.
- `cmd /c "set PYTHONPATH=src&& uv run --no-sync --group dev pytest -q"`: 3.132 bài đạt, 2 bỏ qua, 21 lỗi. Trong đó 9 lỗi khởi tạo tiến trình phụ BGE (`bge_worker_init_stdout_eof`), 11 lỗi do thiếu gói `graphifyy==0.9.50`, và 1 lỗi `uv lock --check` vì `uv.lock` chưa khớp khai báo hiện tại. Không có lỗi ở các kiểm thử RAG liên quan.

## Bàn giao

- Kiểm thử hồi quy mới/được củng cố: `test_exact_identifier_rescue_recovers_candidate_beyond_lexical_window`, `test_exact_identifier_rescue_prioritizes_last_requested_identifier`, `test_full_mode_appends_summary_after_body_results`, `test_full_mode_synthesis_preserves_values_late_in_a_long_chunk`, `test_full_mode_synthesis_prioritizes_last_requested_field_identifier`.
- Thẩm tra độc lập: không có trở ngại cần xử lý.
- Mã nguồn đã được đẩy lên nhánh với mã ghi nhận `a83f8ff4862283522aa5418e1d1233bcb9118ef9`.
