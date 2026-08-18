# Đo Chuẩn Benchmark MVP Giữa AIOS và NotebookLM (AIOS vs NotebookLM MVP Benchmark)

Quy trình đo chuẩn (benchmark) này so sánh hệ thống RAG cục bộ của AIOS với NotebookLM trên một thư mục nguồn MOM/WMS cục bộ đã được người dùng phê duyệt. Nó chỉ đánh giá chất lượng thuần túy. Nó không chứng minh tính tương đương năng lực với NotebookLM.

## Đường Dẫn Dữ Liệu Thực Tế (Real Data Path)

Ví dụ thư mục nguồn cục bộ của người dùng: `[LOCAL_SOURCE_ROOT]`.

Các kết quả đầu ra được sinh ra bắt buộc phải nằm dưới thư mục `local_runs/notebooklm_compare/` (đã được cấu hình gitignore).

## Luồng Hoạt Động của AIOS (AIOS Flow)

1. Tải cấu hình đo chuẩn cục bộ.
2. Khám phá đệ quy các tài liệu dạng văn bản được hỗ trợ.
3. Tạo các đối tượng `RAGChunk` cục bộ với nhãn quyền riêng tư `local_only`.
4. Tìm kiếm cục bộ bằng SQLite FTS/BM25.
5. (Tùy chọn) Áp dụng bộ xếp hạng lại (reranker) tất định cục bộ.
6. Xây dựng các gói bằng chứng (evidence packs).
7. Soạn thảo các bản thảo câu trả lời có trích dẫn tất định cục bộ bằng bộ soạn thảo câu trả lời cục bộ.

## Luồng Hoạt Động của NotebookLM (NotebookLM Flow)

Chỉ sử dụng công cụ CLI `nlm` sau khi đã khám phá năng lực CLI. Nếu CLI cục bộ không thể tự động hóa việc nhập nguồn / truy vấn một cách an toàn, hãy sử dụng sổ tay hướng dẫn thủ công trong [Sổ tay thu thập NotebookLM thủ công](NOTEBOOKLM_MANUAL_COLLECTION_RUNBOOK.md).

## Tạo Câu Hỏi Kiểm Thử (Question Generation)

Bộ tạo câu hỏi lấy mẫu từ tên tài liệu và metadata an toàn từ các tài liệu cục bộ. Nó tạo các prompt theo phong cách Tiếng Việt / Tiếng Anh / Tiếng Nhật bao gồm:

1. Tra cứu trực tiếp (direct lookup)
2. Trích xuất quy trình / bước thực hiện (procedure/step extraction)
3. Điều tra nguyên nhân / kết quả (cause/effect investigation)
4. Tính đầy đủ của bằng chứng (evidence sufficiency)
5. Mối quan hệ xuyên tài liệu (cross-document relation)
6. Không thể trả lời / Chưa đủ bằng chứng (unanswerable/insufficient evidence)

## Thu Thập Câu Trả Lời (Answer Collection)

Các câu trả lời của AIOS được ghi vào tệp JSONL bị gitignore. Các câu trả lời của NotebookLM, nếu thu thập được, cũng được ghi vào JSONL bị gitignore và tuyệt đối không được commit vì chúng có thể chứa nội dung nhạy cảm của công ty.

## Chấm Điểm (Scoring)

Bộ đánh giá tất định chấm điểm từ 0-3 cho các tiêu chí: độ liên quan, tính hữu ích của trích dẫn, tính có căn cứ nguồn, tính hoàn chỉnh, tính trung thực khi chưa đủ bằng chứng, quyền riêng tư / kiểm soát cục bộ, tính hành động cho chủ sở hữu và rủi ro ảo giác (hallucination).

## Chính Sách Tuyên Bố (Claim Policy)

Được phép tuyên bố: "Đo chuẩn AIOS vs NotebookLM MVP", "kết quả ứng viên tự đánh giá", "lượt chạy so sánh với NotebookLM", "báo cáo chất lượng RAG cục bộ".

Nghiêm cấm tuyệt đối trừ khi có bằng chứng đã qua con người đánh giá chứng minh: "Đạt độ tương đương với NotebookLM", "AIOS tốt hơn NotebookLM", hoặc "Thay thế hoàn toàn NotebookLM".

Trạng thái `PASS_CANDIDATE` chỉ có nghĩa là bài tự đánh giá đã đạt. Vẫn bắt buộc phải có sự đánh giá của con người trước khi đưa ra bất kỳ tuyên bố tương đương nào.
