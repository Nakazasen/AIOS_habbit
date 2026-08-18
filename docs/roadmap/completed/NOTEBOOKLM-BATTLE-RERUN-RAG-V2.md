# Chạy Lại Đo Chuẩn So Sánh RAG v2 và NotebookLM (NOTEBOOKLM-BATTLE-RERUN-RAG-V2)

Status: `DONE`

## Mục Tiêu (Goal)

Tạo ra bằng chứng có thể so sánh được, ẩn danh hệ thống (identity-blind) giữa NotebookLM, luồng Workspace Chat hiện tại và ứng viên RAG v2 độc lập. Cổng này đóng lại giao thức đánh giá và lượt chạy bằng chứng; nó không tuyên bố tính tương đương sản phẩm hay tự ý chuyển RAG v2 vào giao diện người dùng chính.

## Giao Thức Đã Triển Khai (Implemented Protocol)

- Thay thế việc chặn cứng độ tương đương 48 nguồn bằng một cuộc kiểm toán năng lực. Sự khác biệt về số lượng nguồn vẫn hiển thị rõ ràng nhưng không làm mất hiệu lực của các quy trình làm việc có bằng chứng tồn tại.
- Phân loại độc lập tính khả dụng của nguồn / quy trình cho NotebookLM, Workspace Chat và RAG v2.
- Thực thi riêng biệt nhánh Workspace Chat hiện tại và nhánh converter / chunker / index / evidence / synthesis của RAG v2 độc lập.
- Giới hạn việc nạp dữ liệu benchmark cục bộ trong nội dung chuẩn tắc `tailieugoc` và loại trừ trạng thái tự sinh, cache, bản nháp và câu trả lời trước đó.
- Thêm cơ chế checkpoint / resume tất định và xử lý thử lại có giới hạn cho NotebookLM.
- Tạo một gói 3 hệ thống ẩn danh ổn định và giữ các gán nhãn tách biệt cho đến khi việc đánh giá độc lập hoàn tất.
- Chỉ nhập điểm số 0–5 trên 8 chiều đánh giá cho các hàng dùng chung, hoàn thành thành công. Loại trừ các lỗi provider và quy trình không áp dụng được.

## Bằng Chứng Nghiệm Thu (Acceptance Evidence)

Bằng chứng riêng tư được lưu giữ dưới các artifact cục bộ bị gitignore trong `local_runs/battle_rag_v2/BATTLE-RAGv2-1784990862-e33e5670/`.
Tuyệt đối không commit câu trả lời thô, nội dung ngữ liệu riêng tư, nhãn gán hay credential lên Git.

- Định danh Notebook và quyền truy cập CLI đã xác thực: PASS.
- Ngữ liệu chuẩn tắc cục bộ: 53 tài liệu đã chuyển đổi / 767 chunk RAG.
- Bộ câu hỏi đóng băng: 12 câu hỏi; hậu tố mã băm `e33e5670`.
- RAG v2: Hoàn thành 12/12 quy trình áp dụng được.
- Workspace Chat: Hoàn thành 12/12 quy trình áp dụng được.
- NotebookLM: Hoàn thành 11/11 quy trình áp dụng được.
- `BQ09`: NotebookLM được đánh giá là `not_applicable` vì là quy trình bản địa của Excel; loại trừ khỏi chất lượng ngữ liệu dùng chung và biểu diễn trong độ bao phủ tiện ích bản địa.
- Lỗi provider trong các checkpoint phục hồi cuối cùng: 0.
- Đánh giá mù độc lập: 11 hàng dùng chung, tất cả đều được nhập thành công.
- Số trận thắng (Wins): NotebookLM 8, RAG v2 2, Workspace Chat 1, Hòa 0.
- Điểm trung bình của 8 chiều tiêu chí: NotebookLM 3.807/5, RAG v2 2.898/5, Workspace Chat 2.841/5.
- RAG v2 có sự cải thiện nhẹ so với luồng sản phẩm hiện tại trên lượt chạy này, nhưng chưa đạt tới chất lượng của NotebookLM. Các khoảng cách lớn nhất đo được là độ hoàn chỉnh, hỗ trợ trích dẫn, tính hành động và khả năng tổng hợp xuyên nguồn.
- Kiểm thử hồi quy RAG / benchmark tập trung: 57 passed.
- Kiểm thử hồi quy toàn bộ repository: 977 passed.
- Hợp đồng tài liệu: PASS.
- Biên dịch: PASS.
- Kiểm toán CLI audit: PASS, không có lỗi hay cảnh báo.

## Quyết Định (Decision)

Giai đoạn đo chuẩn đã hoàn tất và đủ tính tái lập để đóng lại. Bằng chứng hỗ trợ kết luận sản phẩm sau:

- `RAG_V2_READY_BUT_NOT_IN_PRIMARY_UI` dưới góc độ là ứng viên kỹ thuật;
- `NOT_READY` cho tuyên bố đạt độ tương đương với NotebookLM;
- Workspace Chat tuyệt đối không được quảng bá là tương đương NotebookLM chỉ từ một notebook / lượt chạy đơn lẻ này.

## Công Việc Tiếp Theo (Follow-up Work)

- Cải thiện độ phủ bằng chứng và recall truy xuất của RAG v2 cho các câu hỏi có thể trả lời; một vài trận thua xuất phát từ việc từ chối trả lời sai (false insufficiency).
- Cải thiện việc tổng hợp xuyên tài liệu, độ chi tiết trích dẫn và xây dựng câu trả lời hướng quy trình.
- Định nghĩa và kiểm chứng cổng tích hợp tiếp theo trước khi thay thế luồng truy xuất sản xuất của Workspace Chat.
- Duy trì ranh giới bảo mật ưu tiên cục bộ và hợp đồng BrainGateway hiện có.

## Các Loại Trừ Rõ Ràng (Explicit Exclusions)

- Không tải dữ liệu lên NotebookLM hay đồng bộ nguồn.
- Không định tuyến cloud cho bằng chứng `local_only` hoặc `confidential`.
- Không commit artifact benchmark riêng tư thô vào Git.
- Không tự động kích hoạt RAG v2 trong Workspace Chat.
- Không mở cổng A18 hoặc P1.0.

