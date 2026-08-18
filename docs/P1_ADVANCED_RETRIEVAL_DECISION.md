# Quyết Định Về Truy Xuất Nâng Cao Cho P1 (P1 Advanced Retrieval Decision)

## Tóm Tắt Quyết Định (Decision Summary)

- Cơ sở dữ liệu Vector (Vector DB) trước P1.0: `DEFERRED_NOT_P1_BLOCKER` (TẠM HOÃN, KHÔNG CHẶN P1).
- Cơ sở dữ liệu Đồ thị (Graph DB) trước P1.0: `DEFERRED_NOT_P1_BLOCKER` (TẠM HOÃN, KHÔNG CHẶN P1).
- Tương đương năng lực với NotebookLM: `NOT_CLAIMED` (KHÔNG TUYÊN BỐ).

## Cơ Sở Dữ Liệu Vector Có Bắt Buộc Trước P1.0 Không?

Chưa có bằng chứng hiện tại nào chứng minh rằng Vector DB là bắt buộc trước P1.0. Nền tảng SQLite FTS/BM25 cục bộ hiện có, gói bằng chứng và khung đo chuẩn benchmark đã đủ để tiếp tục kiểm chứng quy trình làm việc của chủ sở hữu.

Vector DB chỉ nên được xem xét lại nếu một đợt đo chuẩn benchmark chứng minh rằng việc truy xuất từ khóa / BM25 không thể tìm thấy bằng chứng liên quan cho các tác vụ quan trọng của chủ sở hữu được diễn đạt khác với văn bản gốc.

## Cơ Sở Dữ Liệu Đồ Thị Có Bắt Buộc Trước P1.0 Không?

Chưa có bằng chứng hiện tại nào chứng minh rằng Graph DB là bắt buộc trước P1.0. P1.0 trước hết cần chứng minh quy trình làm việc hằng ngày: Vụ việc (Case) → Bằng chứng (Evidence) → Hành động (Action).

Graph DB chỉ nên được xem xét lại nếu các truy vấn quan hệ xuyên vụ việc trở nên bắt buộc đối với P1 và không thể biểu diễn bằng metadata cục bộ gọn nhẹ.

## Thất Bại Nào Sẽ Biện Minh Cho Việc Cần Truy Xuất Nâng Cao?

- Liên tục bỏ sót trong các đợt đo chuẩn benchmark đối với các câu hỏi tương đương về mặt ngữ nghĩa.
- Chủ sở hữu không thể tìm thấy bằng chứng đã biết thông qua các truy vấn Tiếng Việt / Tiếng Anh hợp lý.
- Gói bằng chứng chứa quá nhiều chunk không liên quan cho việc sử dụng hằng ngày.
- Các câu hỏi quan hệ xuyên vụ việc trở thành bắt buộc đối với các quyết định của P1.0.

## Yêu Cầu Đối Với Đợt Đo Chuẩn Benchmark

- Bộ câu hỏi dữ liệu giả (synthetic) và chỉ chạy cục bộ với dữ liệu thực.
- Các chunk, tài liệu và nhãn trích dẫn kỳ vọng.
- Các câu hỏi thuộc dạng chưa đủ bằng chứng (insufficient-evidence).
- Kiểm tra tỷ lệ đạt về quyền riêng tư.
- So sánh trước / sau với đường cơ sở BM25 hiện tại.

## Chính Sách Dùng Từ Ngữ Về NotebookLM

Cách dùng từ được phép:
- "Gói xuất an toàn cho NotebookLM (NotebookLM-safe export)"
- "Quy trình bằng chứng cục bộ (local evidence workflow)"
- "Đo chuẩn truy xuất có giới hạn (limited retrieval benchmark)"
- "Tiêu chí đo chuẩn theo phong cách NotebookLM (NotebookLM-style benchmark criteria)"

Cách dùng từ nghiêm cấm tuyệt đối trừ khi được chứng minh bằng benchmark và sự nghiệm thu của chủ sở hữu:
- "Tương đương NotebookLM (NotebookLM parity)"
- "Thay thế NotebookLM (NotebookLM replacement)"
- "Tốt hơn NotebookLM (better than NotebookLM)"

## Vì Sao Tạm Hoãn Lại Là Quyết Định An Toàn

Việc tạm hoãn Vector DB và Graph DB giúp P1 tập trung cao độ vào tính khả dụng cho chủ sở hữu, quyền riêng tư, khả năng truy xuất nguồn gốc bằng chứng và kiểm chứng thực tế. Việc thêm các cơ sở dữ liệu lưu trữ nâng cao trước khi có sự nghiệm thu của chủ sở hữu sẽ làm phình to phạm vi và rủi ro mà không chứng minh được nó giải quyết được nút thắt hiện tại.

