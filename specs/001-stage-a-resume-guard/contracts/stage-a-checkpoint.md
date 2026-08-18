# Hợp Đồng Checkpoint Giai Đoạn A (Stage A Checkpoint Contract)

CLI staging benchmark sở hữu `workspace_stage_checkpoint.json` nằm cạnh `workspace_stage_manifest.json`.

- Checkpoint là tệp JSON nguyên tử và là bằng chứng runtime bị bỏ qua (ignored runtime evidence).
- Định danh là đối tượng `workspace_stage_identity` hiện có không thay đổi.
- Trình chạy khởi tạo một checkpoint ở trạng thái `building` trước khi chuẩn bị nguồn.
- Adapter chỉ gọi callback tiến trình của nó sau khi một nguồn đã commit thành công.
- Mỗi callback ghi lại các giá trị `document_id` mờ đã hoàn thành có thứ tự và đẩy nhịp tim không chứa nội dung về phía trước.
- Checkpoint chưa hoàn thành khớp chính xác có thể tiếp tục được. Checkpoint cũ, không đọc được hoặc không khớp sẽ áp dụng fail-closed.
- Lỗi hạn chót của nguồn sẽ ghi trạng thái `failed` với một danh mục an toàn và không tạo ra manifest giai đoạn sẵn sàng.
- Hợp đồng này không tạo provider, không gọi NotebookLM hay kích hoạt tổng hợp.

