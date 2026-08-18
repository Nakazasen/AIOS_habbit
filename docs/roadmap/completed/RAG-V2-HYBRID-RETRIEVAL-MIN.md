# Truy Xuất Kết Hợp Tối Thiểu Cho RAG v2 (RAG-V2-HYBRID-RETRIEVAL-MIN)

Status: `DONE`

## Mục Tiêu (Goal)

Cải thiện khả năng truy xuất RAG v2 tổng quát cục bộ vượt lên trên chỉ mục từ vựng tất định hiện tại mà không làm trôi dạt UI, cloud, dependency hay tinh chỉnh đặc thù ngành.

## Điều Kiện Tiên Quyết (Preconditions)

- Dọn dẹp tuyến công khai kế thừa / tài liệu đã đóng và được kiểm chứng.
- Nền tảng schema / converter / chunker / index của RAG v2 vẫn đạt màu xanh.
- Hợp nhất chính sách tuyến thực tế AI Gateway P0 ở trạng thái `DONE`.

## Phạm Vi Đã Triển Khai (Implemented Scope)

- Truy xuất ứng viên từ vựng tổng quát với tách từ Unicode tokenization.
- Tăng điểm khớp chính xác / metadata tất định: cụm từ văn bản chính xác, tên/đường dẫn nguồn, cấu trúc phần/sheet, loại phần tử bảng, metadata độ mới/độ tin cậy tổng quát tùy chọn.
- Bộ lọc nhãn bảo mật trước khi xếp hạng, bộ lọc đường dẫn tài liệu/nguồn được chọn, và kiểm tra độ mới của dấu vân tay nguồn.
- Giới hạn độ đa dạng nguồn trên mỗi tài liệu (mặc định: tối đa 2 chunk mỗi tài liệu).
- Phân định hòa điểm tất định: điểm giảm dần, sau đó theo ID tài liệu / đường dẫn nguồn / ID chunk tăng dần.
- `SearchSummary` minh bạch với số lượng đã lập chỉ mục / đủ điều kiện / ứng viên / kết quả, phân tích bộ lọc, số lượng bị giới hạn đa dạng, độ bao phủ truy vấn và lý do thiếu dữ liệu an toàn.
- Các kiểu dữ liệu công khai mới: `SearchOptions`, `SearchResult` (mở rộng), `SearchSummary`, `SearchResponse`.
- Bảo toàn API danh sách tương thích ngược `search(query, limit=...)`.
- Kiểm thử tập trung: 18 passed bao gồm xếp hạng cụm từ, tín hiệu metadata, tín hiệu bảng, lọc bảo mật/nguồn/cũ, tính đa dạng, tính tất định và xử lý truy vấn không có token.

## Bằng Chứng Nghiệm Thu (Acceptance Evidence)

- Kiểm thử tập trung chỉ mục / chia chunk / chốt chặn mã cứng RAG v2: **18 passed** in 0.55s.
- Hợp đồng tài liệu: PASS.
- Biên dịch (`py -3 -m compileall src tests`): PASS.
- Toàn bộ bộ kiểm thử: **907 passed** in 12.94s.
- Kiểm toán CLI audit (`py -3 -m aios_habit.cli audit`): PASS, không có lỗi hay cảnh báo.
- Import Workspace Chat: PASS (chỉ có cảnh báo bare-mode của Streamlit như kỳ vọng).
- `git diff --check` và `git diff --cached --check`: PASS.
- Chốt chặn mã cứng (`test_rag_v2_hardcode_guard.py`): PASS; không có thuật ngữ được bảo vệ nào trong mã nguồn hoặc chú thích của RAG v2.

## Các Loại Trừ Rõ Ràng (Explicitly Excluded)

- Không có cơ sở dữ liệu vector, embedding hay lệnh gọi cloud/provider/mạng nào.
- Không thêm dependency mới nào.
- Không thay đổi UI Workspace Chat hay di chuyển runtime; đường dẫn cũ `rag_search.py` vẫn là bộ truy xuất hoạt động của Workspace Chat.
- Không có định tuyến đặc thù dự án, ý định hay mã cứng đặc thù ngành trong RAG v2.
- Không thay đổi trạng thái roadmap/changelog trong cổng triển khai này; đồng bộ trạng thái là thao tác chỉ dành cho tài liệu riêng biệt.

## Tài Liệu Tham Khảo (References)

- Kiến trúc: `docs/rag_v2/RAG_V2_DESIGN.md`
- Các mẫu bên ngoài đã tham khảo: Haystack `DocumentJoiner`, LlamaIndex `QueryFusionRetriever`, tài liệu hướng dẫn tìm kiếm kết hợp Vespa, SQLite FTS5.

