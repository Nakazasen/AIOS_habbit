# Quy tắc Phát triển & Tác tử AIOS WorkLens (Agent Rules)

Tài liệu này quy định các điều luật bị khóa cứng mà toàn bộ các mô hình AI, tác tử phát triển (development agents) và người chỉnh sửa mã nguồn **BẮT BUỘC** phải tuân thủ nghiêm ngặt không có ngoại lệ khi làm việc trên repository `AIOS_habbit`.

---

## 1. Phân định Vai trò Mô hình bị Khóa (Locked Model Roles)

Để ngăn chặn suy thoái mã nguồn (regression), thực thi chắp vá hoặc các xác minh "PASS giả tạo" (fake PASS), các nhiệm vụ phát triển được phân chia nghiêm ngặt theo thế mạnh chuyên môn của mô hình/tác tử:

### A. Chuyên gia Kiểm toán & Đánh giá (Audit Specialist)
- **Vai trò chính:** Kiểm toán chất lượng mã nguồn, đánh giá bảo mật, kiểm tra chống PASS giả tạo và lập luận phân tích kiến trúc.
- **Ràng buộc:**
  - Bắt buộc phải kiểm tra tất cả các tệp đã sửa đổi và chạy các lệnh kiểm tra độc lập.
  - Phải chỉ ra các nguy cơ rò rỉ prompt, quá tải trải nghiệm người dùng (UX overload) và sự thiếu hụt bằng chứng xác thực.
  - Không tự tiện commit hoặc viết mã tính năng trừ khi được yêu cầu các chỉnh sửa nhỏ.
- **Mô hình khuyến nghị hiện tại:** Codex GPT-5.5 hoặc tương đương.

### B. Chuyên gia Thực thi (Execution Specialist)
- **Vai trò chính:** Triển khai tính năng, sửa lỗi (bug fixes), tái cấu trúc mã nguồn (refactor) và viết unit test.
- **Ràng buộc:**
  - Phải tuân thủ nghiêm ngặt theo các bản kế hoạch triển khai (implementation plans) đã được người dùng phê duyệt.
  - Không được bỏ qua việc viết unit test hoặc chạy xác minh lệnh thực tế.
- **Mô hình khuyến nghị hiện tại:** Gemini Flash 3.5 High / Gemini Pro 3.1 hoặc tương đương.

---

## 2. Quy tắc Xác minh & Kiểm thực Bắt buộc (Mandatory Verification)

Không một pull request hay thay đổi mã nguồn nào được phép merge hoặc push nếu không đáp ứng đầy đủ các tiêu chuẩn sau:

1. **Kiểm tra Biên dịch (Compilation Check):** Mã nguồn phải biên dịch sạch sẽ khi chạy `py -3 -m compileall src tests`.
2. **Độ bao phủ Pytest:** Toàn bộ unit test hiện có và bất kỳ bài test mới nào được thêm vào đều phải vượt qua với `py -3 -m pytest -q`.
3. **Kiểm tra CLI Audit Cục bộ:** Chạy `$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit` bắt buộc phải trả về `"status": "PASS"` không có lỗi.
4. **Kiểm tra Import Giao diện Chính:** Chạy `$env:PYTHONPATH="src"; py -3 -c "import aios_habit.workspace_chat_app"` phải chạy thành công không có lỗi.
5. **Kiểm tra Ranh giới Hệ thống Cũ (Legacy Boundary Check):** Các module Workspace Chat được hỗ trợ tuyệt đối không được import `studio` hoặc `case_cockpit`; khi cho dừng một phần cũ phải gỡ bỏ cả đường dẫn khởi chạy lẫn kỳ vọng test lỗi thời.

---

## 3. Quy tắc Bảo mật & Quyền riêng tư Cốt lõi (Bất khả xâm phạm)
- **Tuyệt đối không rò rỉ lên Cloud:** Các mục bằng chứng gắn nhãn `local_only`, văn bản thô trích xuất từ log/bảng tính cục bộ và các thẻ học việc bản nháp/chưa xác nhận **tuyệt đối không bao giờ** được đưa vào prompt gửi ra các dịch vụ cloud bên ngoài (`gemini`, `gpt`, `copilot`, `notebooklm_safe`) hoặc các gói bàn giao cloud_safe.
- **Chỉ dành cho AI Cục bộ:** Dữ liệu nhạy cảm chỉ có thể được đưa vào prompt của `local_ai` nếu người dùng chỉ định rõ ràng `include_local_only=True`.
- **Quy tắc Git-Ignore:** Trong mọi tình huống, dữ liệu hồ sơ sự vụ cục bộ (`local_cases/`), ảnh chụp màn hình thực tế, tệp cơ sở dữ liệu thật hoặc tệp cấu hình `.env` riêng tư không bao giờ được đưa vào theo dõi của Git.

---

## 4. Chính sách Ngôn ngữ & Bản địa hóa Giao diện
- **Ưu tiên Tiếng Việt (Vietnamese First):** Giao diện người dùng phải được bản địa hóa 100% bằng Tiếng Việt.
- **Giải thích Thuật ngữ Kỹ thuật:** Các hằng số kỹ thuật tiếng Anh bắt buộc (như `local_only`, `redacted_export`, `cloud_allowed`) phải có giải thích ngắn gọn bằng Tiếng Việt đi kèm ngay bên cạnh.
- **Không để lộ cảnh báo mã nguồn thô:** Các thông điệp traceback thô hoặc lỗi Python chưa xử lý phải được bắt giữ và hiển thị cho người dùng dưới dạng khối cảnh báo đã được bản địa hóa sạch sẽ.

