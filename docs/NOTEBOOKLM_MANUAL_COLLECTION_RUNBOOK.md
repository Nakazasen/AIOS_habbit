# Sổ Tay Thu Thập Thủ Công NotebookLM (NotebookLM Manual Collection Runbook)

Sử dụng quy trình này khi công cụ `nlm` không thể tự động hóa an toàn việc import / truy vấn / thu thập kết quả đầu ra.

1. Tạo hoặc chọn một sổ ghi chép (notebook) NotebookLM cho đợt so sánh MOM/WMS.
2. Nhập các tài liệu cục bộ đã được phê duyệt từ `[LOCAL_SOURCE_ROOT]` bằng giao diện web NotebookLM hoặc các lệnh `nlm` được hỗ trợ.
3. Mở tệp `local_runs/notebooklm_compare/questions.jsonl` tại máy cục bộ.
4. Đặt từng câu hỏi theo đúng thứ tự đó.
5. Lưu các câu trả lời và trích dẫn vào tệp `local_runs/notebooklm_compare/notebooklm_answers.jsonl`.
6. Tuyệt đối không commit tệp câu trả lời này lên Git.
7. Chạy lệnh `aios-habit notebooklm-compare evaluate` sau khi cả hai tệp câu trả lời của AIOS và NotebookLM đều đã tồn tại.

Tuyệt đối không dán các API key, tệp `.env`, hoặc tài liệu công ty không liên quan. Không tuyên bố tính tương đương chỉ từ một lượt chạy này.
