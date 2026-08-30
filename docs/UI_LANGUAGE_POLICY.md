# Chính Sách Ngôn Ngữ Giao Diện (UI Language Policy)

## Mục Đích (Purpose)

Giao diện người dùng hướng tới chủ sở hữu thông thường mặc định ưu tiên Tiếng Việt (Vietnamese-first). Các định danh của lập trình viên, tên lệnh và đường dẫn tệp được giữ nguyên văn để có thể chạy và tìm kiếm chính xác.

## Tài liệu (cùng luật với giao diện)

Tài liệu người đọc viết tiếng Việt. Luật khóa: `AGENT_RULES.md` mục 4, `CONSTITUTION.md` nguyên tắc 6. File này chỉ bổ sung quy tắc **giao diện**.

## Quy Tắc (Rules)

1. Sử dụng 100% tiếng Việt cho các nhãn, hành động, cảnh báo, trạng thái trống và thông báo lỗi hiển thị cho người dùng. Không dùng câu tiếng Anh làm fallback.
2. Giải thích các thuật ngữ kỹ thuật cần thiết ngay bên cạnh văn bản giao diện; không bắt người dùng phải học các khái niệm RAG, provider, bridge, hash hay gate để phục vụ công việc hằng ngày.
3. Tuyệt đối không làm lộ traceback thô, đường dẫn hệ thống tệp, thông tin bí mật hoặc nội dung cục bộ chưa được làm sạch qua thông báo lỗi thông thường trên UI.
4. Mã lỗi nội bộ và giá trị enum tiếng Anh phải được ánh xạ sang câu tiếng Việt trước khi hiển thị; nếu chưa có ánh xạ thì dùng thông báo tiếng Việt an toàn, không in thẳng giá trị kỹ thuật.
5. Giữ nguyên văn các ví dụ kỹ thuật có thể thực thi, chẳng hạn như `pytest`, `compileall`, `RUN_AIOS_WORKSPACE_CHAT.bat` và `src/aios_habit/workspace_chat_app.py`.
6. Các bài kiểm tra hồi quy có thể kiểm tra mã nguồn, nhưng tuyệt đối không coi giao diện cũ trong lịch sử là giao diện người dùng được hỗ trợ.

