# Kích Hoạt Sản Xuất Truy Xuất Kết Hợp RAG v2 (RAG-V2-HYBRID-PRODUCTION-ACTIVATION)

Status: `COMPLETED — 2026-07-29`

## Mục Tiêu (Goal)

Đưa bộ truy xuất cục bộ đã kiểm chứng mạnh nhất thành hành vi mặc định của Workspace Chat trên laptop văn phòng CPU 16 GB trong khi vẫn duy trì trải nghiệm đơn giản và chất lượng câu trả lời ổn định.

## Hợp Đồng Sản Phẩm (Product Contract)

Người dùng thông thường không nhìn thấy công tắc chuyển đổi hybrid / từ vựng / cũ và không cần hiểu các cờ tính năng (feature flags). Workspace Chat tự động sử dụng chế độ truy xuất sẵn sàng tốt nhất.

Nếu truy xuất chất lượng cao không khả dụng, sản phẩm tuyệt đối không được âm thầm đưa ra câu trả lời yếu hơn rõ rệt dưới dạng tương đương. Hệ thống phải tự động phục hồi, duy trì runtime sẵn sàng gần nhất, hoặc hiển thị thông báo ngắn gọn phi kỹ thuật như: "Tính năng tìm kiếm tài liệu chất lượng cao tạm thời chưa khả dụng; vui lòng thử lại."

Tên chế độ kỹ thuật, đường dẫn mô hình, mã checksum và viễn trắc dự phòng chỉ xuất hiện trong giao diện chẩn đoán của chủ sở hữu / vận hành viên.

## Phạm Vi (Scope)

- Cài đặt hoặc tham chiếu artifact BGE-M3 cục bộ đã kiểm chứng thông qua cấu hình triển khai ổn định.
- Tái sử dụng chỉ mục đã hiện thực hóa và giữ mô hình ở trạng thái ấm thay vì tải lại / xây dựng lại cho mỗi câu hỏi.
- Đo lường khởi động lạnh, truy xuất ấm, mức RAM đỉnh, kích thước chỉ mục, tải CPU và độ trễ câu trả lời đầu cuối trên dòng laptop CPU 16 GB mục tiêu.
- Chạy một đợt canary giới hạn cho chủ sở hữu bằng các tác vụ Workspace Chat thực tế và so sánh độ ổn định câu trả lời với luồng hiện tại.
- Xác định chính sách sức khỏe / phục hồi tự động giúp tránh sự suy giảm chất lượng không rõ nguyên nhân.
- Sau khi chủ sở hữu nghiệm thu, đặt truy xuất hybrid sẵn sàng tốt nhất làm hành vi nội bộ mặc định mà không cần thêm cài đặt cho người dùng thông thường.

## Định Quy Mô Đường Cơ Sở (Baseline Sizing)

- Artifact mô hình BGE-M3 đã kiểm chứng: xấp xỉ **2.3 GB trên ổ đĩa**.
- Độ trễ truy xuất p95 đo được trên CPU ấm trong Gate H: xấp xỉ **1.8 giây** mỗi truy vấn.
- Cấu hình Reranker bị loại trừ khỏi cổng này vì độ trễ đo được lên tới ~174–186 giây p95 và không mang lại cải thiện Recall@10 nào.
- Thời gian câu trả lời đầu cuối cũng bao gồm độ trễ riêng của provider / mô hình sinh câu trả lời.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

- Đường dẫn mô hình, phiên bản revision và mã checksum chính xác vượt qua các kiểm tra sẵn sàng sau khi khởi động lại sạch.
- Bộ nhớ hệ thống và tiến trình ở mức đỉnh vẫn an toàn trên máy 16 GB mà không bị phân trang liên tục hoặc làm mất ổn định các ứng dụng văn phòng khác.
- Khởi động lạnh được đo lường và thông báo; truy xuất ấm đạt mục tiêu được chủ sở hữu phê duyệt, ban đầu là p95 ≤ 3 giây.
- Khởi tạo chỉ mục / mô hình không bị lặp lại cho mỗi câu hỏi.
- Không có sự suy giảm chất lượng âm thầm nào xảy ra xuyên suốt các lần chạy lại bình thường, lỗi mô hình, chỉ mục cũ hoặc thay đổi nguồn.
- Các tác vụ và trích dẫn đại diện của chủ sở hữu đạt kiểm thử E2E trên trình duyệt.
- Hồi quy bảo mật / gateway bằng 0, toàn bộ kiểm thử đạt và chủ sở hữu phê duyệt rõ ràng việc kích hoạt mặc định.

## Các Phi Mục Tiêu (Non-goals)

- Không kích hoạt mô hình reranker đa ngôn ngữ nặng nề trên laptop CPU mục tiêu.
- Không thêm cài đặt kỹ thuật cho người dùng thông thường hay bộ chọn 3 chế độ.
- Không tuyên bố tương đương với NotebookLM mà không có cổng chất lượng câu trả lời mù cùng giao thức sau này.

## Hoàn Tác (Rollback)

Một thay đổi cấu hình nội bộ duy nhất sẽ đưa Workspace Chat trở lại runtime truy xuất ổn định trước đó. Bảo tồn các nguồn, chỉ mục, tệp mô hình và bằng chứng để chẩn đoán; không để lộ các kiểm soát hoàn tác cho người dùng thông thường.

## Kiểm Chứng (Verification)

- Đo chuẩn truy vấn ấm và khởi động sạch trên laptop mục tiêu.
- Thu thập RAM đỉnh / CPU / pagefile trong quá trình lập chỉ mục và truy vấn lặp lại.
- Kiểm thử trình duyệt E2E trên các quy trình đại diện của chủ sở hữu và các luồng phục hồi bắt buộc.
- Kiểm thử adapter / runtime tập trung, hồi quy toàn bộ repository, kiểm tra tài liệu, kiểm toán CLI, kiểm tra import và kiểm tra khoảng trắng Git.

## Bằng Chứng Hoàn Thành (Completion Evidence)

- Trạng thái đo chuẩn sản xuất: `PASS` với đúng cấu hình `bge_m3_hybrid` và không có dự phòng suy giảm nào.
- Truy xuất ấm đo được: trung bình `712.345 ms`, p95 `814.25 ms` so với giới hạn `3,000 ms`.
- Runtime được khởi tạo một lần duy nhất xuyên suốt 8 truy vấn ấm; chuẩn bị và truy vấn là các lệnh worker tách biệt.
- Khởi động lạnh đo được (`35,627.179 ms`) được lập lịch trước trạng thái sẵn sàng và không bị tính vào độ trễ truy vấn.
- Cổng bộ nhớ đạt trên máy 16 GB mục tiêu; tổng hợp mạng và provider giữ trạng thái bị vô hiệu hóa.
- Workspace Chat áp dụng fail-closed trong khi việc chuẩn bị chưa hoàn tất và không để lộ bộ chọn chế độ kỹ thuật cho người dùng thông thường.
- Nghiệm thu trên trình duyệt xác nhận luồng chọn nguồn đơn giản hóa và giao diện sản xuất sạch sẽ.
- Hồi quy UI tập trung đạt `74/74`; toàn bộ hồi quy repository đạt `1,104/1,104`.

