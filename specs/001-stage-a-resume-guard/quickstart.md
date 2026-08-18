# Hướng Dẫn Nhanh: Kiểm Chứng Chuẩn Bị Giai Đoạn A Có Thể Tiếp Tục (Quickstart: Validate Resumable Stage A Preparation)

1. Chạy các bài kiểm thử staging và adapter tập trung:

   ```powershell
   .venv\Scripts\python.exe -m pytest tests\test_workspace_chat_rag_v2_adapter.py tests\test_battle_notebooklm_rag_v2.py -q
   ```

2. Xác nhận một sự gián đoạn giả lập sẽ ghi một checkpoint khớp định danh, sau đó tiếp tục mà không gửi lại tài liệu đã commit đầu tiên.

3. Xác nhận một sự cố hết thời gian chuẩn bị giả lập sẽ khiến checkpoint ở trạng thái failed và không tạo ra manifest staging sẵn sàng.

4. Chỉ chạy Giai đoạn A thực tế sau khi các bằng chứng sản xuất đã niêm phong gốc và các artifact tham chiếu NotebookLM bất biến đã được khôi phục và kiểm chứng. Sử dụng `local_only`; tuyệt đối không gọi Giai đoạn B.

