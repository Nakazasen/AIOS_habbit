# Sao Lưu và Phục Hồi (Backup and Restore)

Status: `ACTIVE`
Owner role: Local data owner / operator
Last reviewed: 2026-07-25
Review cadence: Before release and after a persistent-store change
Last synthetic drill: 2026-07-25 — PASS (six Workspace Chat JSONL entity types and one SQLite index/search)

## Phạm vi và Giới hạn (Scope and Limits)

AIOS WorkLens hoạt động theo nguyên tắc ưu tiên cục bộ (local-first). Việc sao lưu do chủ sở hữu tự thực hiện và có thể chứa thông tin riêng tư. Tuyệt đối không lưu bản sao lưu vào Git, artifact của CI, đám mây công cộng hay issue hỗ trợ kỹ thuật trừ khi chủ sở hữu đã phê duyệt riêng một đích đến được bảo vệ.

Quy trình này áp dụng cho trạng thái JSONL của Workspace Chat được hỗ trợ và chỉ mục SQLite RAG do caller quản lý. Tài liệu này không cam kết khả năng khôi phục tài liệu nguồn mà chủ sở hữu không còn lưu giữ hoặc chỉ mục mà dữ liệu đầu vào để tái tạo (rebuild) đã mất.

## Kiểm kê Trạng thái Dữ liệu (State Inventory)

| Trạng thái | Khái niệm vị trí | Khuyến nghị sao lưu | Khả năng tái tạo |
|---|---|---|---|
| Sổ ghi chép, tin nhắn, nguồn, lựa chọn Workspace Chat | `local_cases/workspace_chat/` | Sao lưu toàn bộ thành một thư mục | Không thể tự động tái tạo từ các tệp nguồn |
| Chỉ mục RAG v2 SQLite | Đường dẫn CSDL do caller chỉ định tường minh | Sao lưu khi chi phí lập lại chỉ mục lớn | Chỉ có thể tái tạo từ các đầu vào nguồn/chunk sẵn có |
| Tài liệu nguồn riêng tư | Vị trí cục bộ do chủ sở hữu chọn | Theo chính sách của chủ sở hữu | Nguồn gốc; tuyệt đối không sao chép vào repo |
| Cấu hình / Thông tin xác thực | Biến môi trường / Kho bí mật của chủ sở hữu | Tuân thủ chính sách secret của chủ sở hữu | Không bao giờ đưa vào bản sao lưu mặc định |
| Kết quả benchmark/chẩn đoán `local_runs/` | Thư mục đầu ra cục bộ (được gitignore) | Tùy chọn theo từng trường hợp | Thường có thể tái tạo lại được |

## Quy trình Sao Lưu (Backup Procedure)

1. Đóng Workspace Chat và tất cả các tiến trình đang sử dụng cơ sở dữ liệu SQLite đã chọn.
2. Chọn một đích đến được mã hóa hoặc do chủ sở hữu kiểm soát nằm ngoài repository và ngoài thư mục đồng bộ công cộng (trừ khi được phê duyệt rõ ràng).
3. Sao chép toàn bộ thư mục `local_cases/workspace_chat/` thành một đơn vị có gắn dấu thời gian. Bảo toàn tên tệp và mã hóa UTF-8; không chỉnh sửa tệp JSONL trong khi sao chép.
4. Nếu cần, sao chép cơ sở dữ liệu SQLite RAG đã chọn cùng với mọi tệp SQLite journal/WAL trong khi cơ sở dữ liệu đang đóng.
5. Chỉ ghi nhận bằng chứng không nhạy cảm cục bộ: ngày sao lưu, loại kho lưu trữ, trạng thái thành công/thất bại và kết quả kiểm tra khôi phục. Tuyệt đối không ghi nội dung nguồn hoặc API key.
6. Xác minh rằng đích đến không bị Git theo dõi: chạy `git status --short --ignored` trong repository và đảm bảo không có đường dẫn sao lưu nào bị đưa vào stage.

## Quy trình Phục Hồi (Restore Procedure)

1. Dừng Workspace Chat và tạo một bản sao an toàn của thư mục cục bộ hiện tại.
2. Khôi phục bản sao lưu vào chính xác vị trí kho lưu trữ cục bộ; tuyệt đối không gộp thủ công các phần tệp JSONL.
3. Khởi động Workspace Chat và xác minh danh sách sổ ghi chép/cuộc trò chuyện dự kiến hiển thị bình thường mà không làm lộ nội dung nguồn cho provider.
4. Đối với chỉ mục SQLite, chỉ mở bằng phiên bản ứng dụng tương thích/hiện tại, chạy kiểm tra nhanh (smoke test) với count/search bằng truy vấn tổng hợp hoặc truy vấn cục bộ được chủ sở hữu duyệt, sau đó đóng lại an toàn.
5. Nếu khôi phục thất bại, hãy giữ nguyên bản sao bị lỗi, ghi lại tóm tắt lỗi an toàn và làm theo tài liệu [khắc phục sự cố](TROUBLESHOOTING.md). Tuyệt đối không xóa bản sao duy nhất của chủ sở hữu như một nỗ lực cứu vãn.

## Sự cố Hỏng Dữ liệu và Tái tạo (Corruption and Rebuild)

- Lỗi phân tích cú pháp JSONL là một sự cố: giữ lại tệp bị ảnh hưởng và khôi phục bản sao lưu tốt đã biết; tuyệt đối không âm thầm loại bỏ các bản ghi.
- Chỉ mục RAG bị hỏng chỉ có thể được thay thế sau khi chủ sở hữu xác nhận tồn tại đầu vào nguồn/chunk để tái tạo. Chỉ mục mới phải được tạo tại một đường dẫn cục bộ rõ ràng và kiểm tra bằng chứng count/search.
- Tự động di chuyển/tái tạo hiện không phải là một cam kết bảo đảm.

## Bằng chứng Diễn tập Khôi phục (Restore Drill Evidence)

Một đợt diễn tập tổng hợp đã được thực hiện vào ngày 2026-07-25 chỉ trong một thư mục tạm thời. Đợt diễn tập đã ghi và khôi phục một bản ghi tổng hợp trong từng phân loại lưu trữ bền vững của Workspace Chat (sổ ghi chép, cuộc trò chuyện, tin nhắn, nguồn tạm thời, nguồn sổ ghi chép và lựa chọn nguồn), sau đó khôi phục một chunk RAG SQLite tổng hợp và xác minh `count()` cùng với tìm kiếm từ vựng `search()`.

Đợt diễn tập không đọc, ghi hoặc xóa `local_cases/`, tệp thật của chủ sở hữu, API key hay dữ liệu runtime thực tế. Nó chứng minh cấu trúc sao chép/khôi phục thủ công theo tài liệu hoạt động đúng với hợp đồng loader/index hiện tại; nó **không** chứng minh tính toàn vẹn của dữ liệu thật, mã hóa sao lưu, RTO/RPO, tính tương thích đa phiên bản hay khả năng khởi động ứng dụng không cần provider trên dữ liệu của chủ sở hữu.

Trước khi tuyên bố quy trình này hiệu quả cho một schema lưu trữ bền vững đã thay đổi, bắt buộc phải chạy một đợt diễn tập tổng hợp mới và tuân thủ [khả năng tương thích di chuyển dữ liệu](DATA_MIGRATION_COMPATIBILITY.md). Việc diễn tập bằng dữ liệu thật của chủ sở hữu là tùy chọn và bắt buộc phải diễn ra hoàn toàn cục bộ.

## Mục tiêu Khôi phục (Recovery Objectives)

RTO và RPO ở trạng thái `OWNER_DECISION_REQUIRED` (Yêu cầu quyết định từ chủ sở hữu). Tài liệu này định nghĩa một quy trình thủ công cục bộ với nỗ lực tối đa; không hứa hẹn thời gian khôi phục cố định hay đảm bảo không mất mát dữ liệu (zero data loss).

