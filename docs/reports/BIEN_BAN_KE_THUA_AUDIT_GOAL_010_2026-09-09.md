# Biên bản kế thừa kiểm toán Goal 010 ngày 2026-09-09

**Status: CHƯA NGHIỆM THU**

Biên bản này chốt trạng thái làm việc để có thể tiếp tục ở máy khác mà không làm mất định hướng đã thống nhất. Đây là một điểm lưu công việc đang làm, không phải tuyên bố tính năng đã hoàn thành hay sẵn sàng vận hành.

## 1. Ý chí kiểm toán cần được giữ nguyên

Mục tiêu của Goal 010 là giúp một người hoặc một nhóm nhỏ phỏng vấn chuyên gia, xem lại nội dung, ghi nhận quyết định và đưa kiến thức đã được cân nhắc vào thư viện. Chương trình phải dễ dùng với người không chuyên công nghệ và không được dựng thêm một hệ quản trị doanh nghiệp khi chưa có nhu cầu thật.

Các quyết định đã chốt:

- Không xây hệ tài khoản, đăng nhập, RBAC, phân quyền NAS hay cơ chế một máy ghi cố định trong phiên bản này.
- Không coi tên người nhập trên giao diện là bằng chứng xác thực danh tính. Tên chỉ dùng để ghi nhận ai chịu trách nhiệm cho quyết định.
- Thư viện có hai cách dùng dễ hiểu: cá nhân trên máy hiện tại hoặc dùng chung với nhóm tin cậy. Không đặt rào cản kỹ thuật khiến người dùng cá nhân phải nhờ IT.
- Trong nhóm tin cậy, nhiều người có thể thao tác. Khi có xung đột ghi thật sự thì báo bằng tiếng Việt và cho người dùng thử lại; không khóa cứng một người viết duy nhất.
- Mỗi quyết định đưa kiến thức vào thư viện phải lưu tối thiểu: người quyết định, ngày giờ, mức tự tin, nội dung quyết định và nguồn bằng chứng. Người quyết định chịu trách nhiệm xem lại câu trả lời trước khi ghi.
- Luồng chính chỉ nên có bốn chặng dễ hiểu: thu thập nội dung, xem bản chép lời, xem bản nháp kiến thức, quyết định lưu vào thư viện.
- Mặc định ưu tiên nhập văn bản. Ghi âm là lựa chọn bổ sung, không được biến thành điều kiện bắt buộc.
- Không đưa mã gói, mã băm, trạng thái kỹ thuật, phạm vi quyền, ngân sách hay chi tiết phục hồi lên luồng chính. Chỉ hiện khi thật sự cần xử lý sự cố.
- Không đánh đổi an toàn dữ liệu lấy giao diện đơn giản: các thao tác ghi, xuất bản và thu hồi vẫn phải có khả năng phục hồi rõ ràng.
- Không thêm microservice, hàng đợi, dịch vụ định danh hoặc lớp trừu tượng mới nếu chưa có một lỗi hay tiêu chí nghiệm thu cụ thể buộc phải làm.

Tiêu chuẩn ra quyết định cho lượt sau: nếu một biện pháp không giúp người dùng hiểu hơn, không ngăn mất dữ liệu, và không trực tiếp thỏa tiêu chí nghiệm thu thì chưa làm.

## 2. Trạng thái đã đạt trong điểm lưu này

- T083–T109 vẫn để trạng thái chưa hoàn thành; không còn tuyên bố hoàn tất khi thiếu bằng chứng.
- Cờ `FEATURE_EXPERT_MULTI_USER` đã được tách khỏi cờ bật Goal 010.
- Các tuyến giao diện chính đã chuyển sang dùng `service.store` và `service.actor` ở nhiều vị trí lỗi.
- Kho dữ liệu đã có hàm chọn thư viện cá nhân hoặc dùng chung và có bài kiểm tra chuyển qua lại.
- Khi mất tệp bản chép lời, kho dữ liệu báo lỗi thay vì trả nội dung rỗng như thể hợp lệ.
- Tên tệp bản chép lời đã được giới hạn ký tự an toàn hơn.
- Chế độ giả lập được tách rõ; đường chạy dùng thật đóng an toàn khi dịch vụ chưa sẵn sàng.
- Xuất bản đã lấy quyền ghi trước khi sao lưu và đã bỏ cách chấp nhận bằng từ khóa đơn giản.
- Thu hồi đã tìm đúng thêm tên tệp theo `artifact_id` và thực hiện kiểm tra tính toàn vẹn SQLite thật.
- Tài liệu Goal 010 đã chuyển định hướng sang nhóm tin cậy, ghi nhận trách nhiệm và giao diện bốn chặng.

## 3. Các điểm chặn còn phải xử lý

### 3.1 Bản chép lời và di chuyển dữ liệu

- `expert_interview_repository.py` vẫn ghi trực tiếp vào tệp đích bằng `write_bytes`; chưa dùng tệp tạm rồi thay thế nguyên tử. Mất điện, dừng tiến trình hoặc hai lượt ghi gần nhau vẫn có thể tạo tệp dở hay phục hồi đè lên dữ liệu mới.
- `_apply_v8` trong `workspace_case_migrations.py` ghi tệp bên ngoài giao dịch SQLite. Khi giao dịch cơ sở dữ liệu quay lui, tệp đã tạo không được phục hồi hoặc xóa tương ứng.
- Tên tệp trong migration vẫn ghép trực tiếp từ `session_id` và `receipt_id`, chưa áp dụng cùng quy tắc làm sạch như đường ghi mới.
- Xử lý `ON CONFLICT(receipt_id)` chưa đối chiếu khóa chống lặp hoặc nội dung đầu vào. Cùng một mã biên nhận nhưng nội dung khác có thể làm bản chép lời và siêu dữ liệu không còn khớp nhau.

### 3.2 Xuất bản và thu hồi

- `knowledge_publication.py` vẫn ghi trực tiếp Markdown và SQLite đang dùng; chưa có vùng chuẩn bị rồi đổi ảnh chụp nhất quán.
- Khi xuất bản lỗi, mã hiện phục hồi tệp SQLite trong lúc kết nối có thể vẫn đang mở. Trên Windows, thao tác ghi đè có thể thất bại.
- Xuất bản lại cùng `artifact_id` và phiên bản có thể ghi đè Markdown cũ; khi quay lui, bản cũ chưa chắc được khôi phục.
- Thu hồi xác nhận thay đổi cơ sở dữ liệu trước khi xóa tệp. Nếu xóa tệp thất bại, cơ sở dữ liệu và tệp có thể lệch nhau.
- Lỗi xóa chỉ mục vẫn có nhánh `except Exception: pass`; hệ thống có thể báo đã thu hồi trong khi mẩu chỉ mục còn tồn tại.

### 3.3 Hợp đồng quyết định và giao diện

- Chưa có mô hình `DecisionRecord` hoàn chỉnh để lưu người quyết định, ngày giờ, mức tự tin, quyết định và nguồn.
- Cờ Goal 010 chưa được nối vào ứng dụng để thật sự ẩn hoặc chặn tính năng khi tắt.
- Chọn thư viện cá nhân/dùng chung mới có ở tầng kho dữ liệu, chưa có giao diện đơn giản cho người dùng.
- `workspace_case_ui.py` còn tham chiếu `service.actor_context.actor_id` trong đường tạo kế hoạch phỏng vấn; đường này có thể lỗi khi gửi biểu mẫu thật.
- Giao diện vẫn còn các khái niệm không phù hợp người dùng phổ thông: chuyên gia được ủy quyền, phạm vi, ngân sách, âm thanh mẫu, mã gói và mã kỹ thuật.

## 4. Bằng chứng xác minh tại thời điểm chốt

Đã chạy trên Python 3.11.15:

- `uv lock --check`: thành công.
- `uv run --no-sync --group dev python -m compileall -q src tests`: thành công.
- `uv run --no-sync --group dev python scripts/check_user_facing_vietnamese.py`: `PASS`.
- `uv run --no-sync --group dev python -m aios_habit.cli audit`: `status` là `PASS`.
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"`: thành công.
- Nhóm kiểm tra bản chép lời, quyền riêng tư, chuyển đổi âm thanh và migration: 43 bài đạt.
- Nhóm kiểm tra xuất bản, phục hồi, giao diện và kho Workspace Chat: 95 bài đạt.

Chưa chạy lại toàn bộ `pytest -q` trên snapshot này. Một lượt trước đó mất quá nhiều thời gian và không đại diện cho mã hiện tại. Vì vậy không được suy diễn các kết quả hẹp ở trên thành `PASS` toàn chương trình.

## 5. Phạm vi của commit điểm lưu

Commit điểm lưu chỉ gồm tài liệu, mã nguồn và bài kiểm tra liên quan trực tiếp đến Goal 010 cùng biên bản này. Không đưa vào commit:

- thay đổi trong `.agents/`;
- `local_tools/` và `vendor/wheels/`;
- các wheel trong `vendor/wheels_linux/`;
- thay đổi checksum mô hình, `workspace_chat_rag_v2_deployment.py` và `uv.lock` chưa có bằng chứng nguồn rõ ràng;
- `.env`, `local_cases/`, `local_runs/`, dữ liệu thật hoặc nội dung `local_only`.

Các tệp bị loại khỏi commit vẫn có thể còn trong cây làm việc của máy hiện tại. Không được dùng `reset --hard`, xóa hoặc ghi đè chúng khi chưa xác định chủ sở hữu.

## 6. Thứ tự tiếp tục đề xuất

1. Chụp lại `git status -sb`, đọc biên bản này và xác nhận đang ở đúng nhánh.
2. Sửa tham chiếu `service.actor_context` và nối cờ Goal 010 để loại lỗi chạy cơ bản.
3. Hoàn thiện `DecisionRecord` tối thiểu, không thêm tài khoản hoặc phân quyền.
4. Nối lựa chọn thư viện cá nhân/dùng chung vào giao diện bốn chặng.
5. Làm ghi bản chép lời và migration có khả năng phục hồi nhất quán.
6. Sửa thứ tự giao dịch xuất bản/thu hồi và loại bỏ nhánh nuốt lỗi.
7. Rút gọn giao diện bằng một lượt thử tay với người không chuyên công nghệ.
8. Chỉ sau đó chạy toàn bộ cổng chất lượng và giao một người khác kiểm toán độc lập.

## 7. Lệnh xác minh cho lượt kế thừa

```powershell
git status -sb
uv run --no-sync --group dev python --version
uv lock --check
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q tests/test_expert_interview_fixture_hygiene.py tests/test_expert_interview_privacy.py tests/test_local_transcription.py tests/test_workspace_case_migrations.py
uv run --no-sync --group dev pytest -q tests/test_knowledge_publication.py tests/test_knowledge_publication_recovery.py tests/test_workspace_case_ui.py tests/test_workspace_chat_app_smoke.py tests/test_workspace_chat_store.py
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
```

Ngoài kiểm tra tự động, cần đi thử bằng giao diện các tình huống: dùng thư viện cá nhân; chuyển sang thư viện dùng chung; nhập nội dung bằng văn bản; xem và sửa bản chép lời; ghi quyết định có tên, ngày và mức tự tin; xuất bản; thu hồi; xử lý xung đột ghi; khởi động lại rồi đọc lại dữ liệu.
